"""Quality scoring and validation for generated digests.

Contains:
  - _check_digest_quality: main quality gate (LLM-based scoring)
  - Score normalizers: _normalize_scope, _normalize_quality_issue, etc.
  - Score components: _compute_structure_score, _compute_traceability_score, _compute_locale_score
  - Penalty engine: _apply_issue_penalties_and_caps, _extract_structured_issues
  - Blockers: _find_digest_blockers, _check_structural_penalties

Phase 2 will add validate_citation_urls() here.

Extracted from pipeline.py during 2026-04-15 Phase 1.
External callers should still import from services.pipeline (re-exported).
"""
import asyncio
import logging
import re
import time
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from core.config import settings
from models.news_pipeline import ClassifiedGroup, PersonaOutput
from services.agents.client import (
    build_completion_kwargs,
    extract_usage_metrics,
    get_openai_client,
    merge_usage_metrics,
    parse_ai_json,
    with_flex_retry,
)

# _log_stage remains in pipeline.py (defined early, before re-export block).
from services.pipeline import _log_stage  # type: ignore[attr-defined]

# Digest helpers moved to pipeline_digest.py (no cycle: pipeline_quality does
# not import from pipeline_digest and vice versa).
from services.pipeline_digest import (
    _extract_digest_items,
    _map_digest_items_to_group_indexes,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Group 1 — Quality payload helpers
# ---------------------------------------------------------------------------

def _body_paragraphs_for_quality(content: str) -> list[str]:
    """Extract prose-like body paragraphs for quality heuristics."""
    if not content:
        return []
    paragraphs: list[str] = []
    for block in re.split(r"\n\s*\n", content):
        text = block.strip()
        if not text:
            continue
        if text.startswith("## ") or text.startswith("### "):
            continue
        if text.startswith(">"):
            continue
        if re.match(r"^[-*]\s", text) or re.match(r"^\d+\.\s", text):
            continue
        paragraphs.append(text)
    return paragraphs


def _build_body_quality_payload(persona_name: str, persona_output: PersonaOutput) -> str:
    """Build a bilingual body-scoring payload for one persona.

    Payload has explicit SCOPE boundaries so the LLM judge evaluates each
    locale independently — Apr 22 regression: judge saw English blockquotes
    in the EN section and flagged them as KO locale_integrity violations.
    The `scan-this` / `do-not-scan` labels anchor the locale_integrity rule
    to the KO section only.
    """
    return (
        f"Persona: {persona_name}\n\n"
        "=== EN BODY — scan only for en-scoped issues; English quotes here are expected ===\n"
        f"{persona_output.en.strip()}\n\n"
        "=== KO BODY — scan THIS section (and only this section) for locale_integrity (English leakage into Korean) ===\n"
        f"{persona_output.ko.strip()}"
    ).strip()


def _build_frontload_quality_payload(frontload: dict[str, Any] | None) -> str:
    """Build a scoring payload for title/excerpt/focus items."""
    frontload = frontload or {}
    focus_items_en = "\n".join(f"- {item}" for item in (frontload.get("focus_items") or []))
    focus_items_ko = "\n".join(f"- {item}" for item in (frontload.get("focus_items_ko") or []))
    return (
        "=== EN HEADLINE ===\n"
        f"{frontload.get('headline', '')}\n\n"
        "=== KO HEADLINE ===\n"
        f"{frontload.get('headline_ko', '')}\n\n"
        "=== EN EXCERPT ===\n"
        f"{frontload.get('excerpt', '')}\n\n"
        "=== KO EXCERPT ===\n"
        f"{frontload.get('excerpt_ko', '')}\n\n"
        "=== EN FOCUS ITEMS ===\n"
        f"{focus_items_en}\n\n"
        "=== KO FOCUS ITEMS ===\n"
        f"{focus_items_ko}"
    ).strip()


# ---------------------------------------------------------------------------
# Group 2 — Score normalizers & penalty engine
# ---------------------------------------------------------------------------

_CANONICAL_SCOPES = {
    "expert_body", "learner_body", "frontload", "ko", "en",
}


def _normalize_scope(raw_scope: Any, default_scope: str) -> str:
    """Pick a single canonical scope from LLM output.

    LLM judges sometimes return combined scopes like "expert_body|ko|en" or
    "frontload en". Split on pipe/comma/whitespace, then pick the first
    canonical scope. Fall back to the first non-empty token, or default.
    """
    if not raw_scope:
        return default_scope
    tokens = [t for t in re.split(r"[|,\s]+", str(raw_scope).lower()) if t]
    if not tokens:
        return default_scope
    for token in tokens:
        if token in _CANONICAL_SCOPES:
            return token
    return tokens[0]


def _normalize_quality_issue(issue: Any, default_scope: str) -> dict[str, str]:
    """Normalize free-form or structured issues into a consistent schema."""
    if isinstance(issue, dict):
        severity = str(issue.get("severity") or "minor").lower()
        if severity not in {"major", "minor"}:
            severity = "minor"
        return {
            "severity": severity,
            "scope": _normalize_scope(issue.get("scope"), default_scope),
            "category": str(issue.get("category") or "general"),
            "message": str(issue.get("message") or issue.get("text") or "").strip(),
        }
    return {
        "severity": "minor",
        "scope": default_scope,
        "category": "general",
        "message": str(issue or "").strip(),
    }


def _extract_structured_issues(raw_issues: Any, default_scope: str) -> list[dict[str, str]]:
    """Normalize judge issues into deterministic structured records."""
    if not raw_issues:
        return []
    issues = raw_issues if isinstance(raw_issues, list) else [raw_issues]
    normalized = [
        _normalize_quality_issue(issue, default_scope)
        for issue in issues
    ]
    return [issue for issue in normalized if issue["message"]]


def _aggregate_subscores(data: dict) -> int:
    """Aggregate nested rubric sub-scores into a single 0-100 total.

    Expected shape (handbook-pattern, adopted for news in NP-QUALITY-06):
    {
      "structural_completeness": {
        "sections_present": {"evidence": "...", "score": 0-10},
        "section_depth":    {"evidence": "...", "score": 0-10}
      },
      "source_quality": { ... },
      ...
      "issues": [...]
    }

    Algorithm: collect every numeric `score` from nested `{evidence, score}`
    dicts, average over sub-score count, multiply by 10 to normalize to 0-100.

    Returns 0 if no sub-scores found (caller falls back to legacy `data["score"]`).
    """
    scores: list[float] = []
    for group_key, group_val in (data or {}).items():
        # `community_pulse` is NQ-40 Phase 2a measurement-only: sub-scores are
        # collected/persisted via expert_breakdown but excluded from the total
        # until the 2-week observation window closes (~2026-05-06) and Phase 2b
        # decides weighting. See vault/09-Implementation/plans/2026-04-22-nq-40-phase-2-cp-quality.md
        if group_key in {"issues", "score", "subscores", "community_pulse"}:
            continue
        if not isinstance(group_val, dict):
            continue
        for sub_val in group_val.values():
            if isinstance(sub_val, dict) and isinstance(sub_val.get("score"), (int, float)):
                # Clamp to 0-10 defensively (LLM should already stay in range)
                scores.append(max(0.0, min(10.0, float(sub_val["score"]))))
    if not scores:
        return 0
    avg_0_to_10 = sum(scores) / len(scores)
    return round(avg_0_to_10 * 10)


def _apply_issue_penalties_and_caps(
    base_score: int,
    issues: list[dict[str, str]],
) -> tuple[int, int, list[str]]:
    """Apply deterministic issue penalties and score caps."""
    penalty = 0
    caps: list[tuple[int, str]] = []
    for issue in issues:
        severity = issue.get("severity", "minor")
        scope = issue.get("scope", "")
        category = issue.get("category", "")
        if severity == "major":
            penalty += 5
            if category in {"source", "factuality", "fabrication"}:
                caps.append((84, "major_source_cap_84"))
            if scope == "frontload" and category in {"overclaim", "calibration", "clarity"}:
                # Below auto_publish_threshold (85) so the cap actually blocks
                # auto-publish rather than just nominally flagging the issue.
                caps.append((84, "frontload_overclaim_cap_84"))
            if category == "locale" or scope == "ko":
                # Below auto_publish_threshold (85). Locale leakage (e.g.,
                # English in KO body, Apr 19 Community Pulse incident) is a
                # hard failure for reader trust — should never auto-publish.
                caps.append((84, "locale_quality_cap_84"))
            if scope == "learner_body" and category == "accessibility":
                caps.append((92, "learner_accessibility_cap_92"))
        else:
            penalty += 2

    penalty = min(penalty, 20)
    penalized_score = max(0, base_score - penalty)
    if not caps:
        return penalized_score, penalty, []
    cap_score, _label = min(caps, key=lambda item: item[0])
    final_score = min(penalized_score, cap_score)
    # Dedup labels and return strictest cap first (smallest cap value).
    ordered_unique = sorted(set(caps), key=lambda item: (item[0], item[1]))
    return final_score, penalty, [label for _, label in ordered_unique]


def _compute_weekly_structure_score(
    en_expert: str, ko_expert: str, en_learner: str, ko_learner: str,
) -> int:
    """Weekly structure score (0-15): 4 bodies × section + heading counts.

    Weekly recap has 7 expected ## sections (This Week in One Line, Week in
    Numbers, Top Stories, Trend Analysis, Watch Points, Open Source Spotlight,
    So What Do I Do? / What Can I Try?) and Top Stories has 5-7 ### headlines.

    Deductions per body:
    - blank body: -3
    - <5 `## ` sections (out of 7 expected): -2
    - 5-6 `## ` sections: -1
    - <5 `### ` headings: -1 (Top Stories expected 5-7 items)

    Max loss per body: -4. Total max loss: -16, floored at 0.
    """
    score = 15
    for body in (en_expert, ko_expert, en_learner, ko_learner):
        if not body or not body.strip():
            score -= 3
            continue
        lines = body.splitlines()
        h2_count = sum(1 for line in lines if line.startswith("## "))
        if h2_count < 5:
            score -= 2
        elif h2_count < 7:
            score -= 1
        h3_count = sum(1 for line in lines if line.startswith("### "))
        if h3_count < 5:
            score -= 1
    return max(0, score)


def _compute_weekly_traceability_score(
    en_expert: str, ko_expert: str, en_learner: str, ko_learner: str,
) -> int:
    """Weekly citation coverage score (0-15): ratio of paragraphs with [N](URL)
    markers across all 4 bodies, scaled to 15.
    """
    citation_re = re.compile(r"\[\d+\]\(https?://[^)]+\)")
    paragraphs: list[str] = []
    for body in (en_expert, ko_expert, en_learner, ko_learner):
        if body:
            paragraphs.extend(_body_paragraphs_for_quality(body))
    if not paragraphs:
        return 0
    cited = sum(1 for p in paragraphs if citation_re.search(p))
    return max(0, min(15, round(15 * cited / len(paragraphs))))


def _compute_weekly_locale_score(
    en_expert: str, ko_expert: str, en_learner: str, ko_learner: str,
) -> int:
    """Weekly locale-alignment score (0-10): EN/KO symmetry per persona + KO ###
    headings must contain Hangul.

    Each persona (expert, learner) evaluated independently.
    """
    score = 10
    hangul_re = re.compile(r"[\u3131-\u318E\uAC00-\uD7A3]")
    for en, ko in ((en_expert, ko_expert), (en_learner, ko_learner)):
        if not en.strip() or not ko.strip():
            score -= 3
            continue
        en_sections = [line for line in en.splitlines() if line.startswith("## ")]
        ko_sections = [line for line in ko.splitlines() if line.startswith("## ")]
        if abs(len(en_sections) - len(ko_sections)) >= 2:
            score -= 2
        ko_headings = [line for line in ko.splitlines() if line.startswith("### ")]
        if ko_headings and any(not hangul_re.search(line) for line in ko_headings):
            score -= 2
    return max(0, score)


def _compute_structure_score(personas: dict[str, PersonaOutput]) -> int:
    """Compute a lightweight deterministic structure score out of 15."""
    score = 15
    for persona_name in ("expert", "learner"):
        output = personas.get(persona_name)
        if not output:
            score -= 4
            continue
        for locale, content in (("en", output.en), ("ko", output.ko)):
            if not content.strip():
                score -= 2
                continue
            if "## " not in content:
                score -= 1
            if "### " not in content:
                score -= 1
            if len(_body_paragraphs_for_quality(content)) < 3:
                score -= 1
    return max(0, score)


def _compute_traceability_score(personas: dict[str, PersonaOutput]) -> int:
    """Compute citation coverage score out of 15."""
    citation_re = re.compile(r"\[\d+\]\(https?://[^)]+\)")
    paragraphs: list[str] = []
    for output in personas.values():
        if not output:
            continue
        paragraphs.extend(_body_paragraphs_for_quality(output.en))
        paragraphs.extend(_body_paragraphs_for_quality(output.ko))
    if not paragraphs:
        return 0
    cited = sum(1 for paragraph in paragraphs if citation_re.search(paragraph))
    ratio = cited / len(paragraphs)
    return max(0, min(15, round(15 * ratio)))


def _compute_locale_score(personas: dict[str, PersonaOutput]) -> int:
    """Compute locale-alignment score out of 10."""
    score = 10
    hangul_re = re.compile(r"[\u3131-\u318E\uAC00-\uD7A3]")
    for output in personas.values():
        if not output:
            score -= 3
            continue
        if not output.en.strip() or not output.ko.strip():
            score -= 3
            continue
        en_sections = [line for line in output.en.splitlines() if line.startswith("## ")]
        ko_sections = [line for line in output.ko.splitlines() if line.startswith("## ")]
        if abs(len(en_sections) - len(ko_sections)) >= 2:
            score -= 2
        ko_headings = [line for line in output.ko.splitlines() if line.startswith("### ")]
        if ko_headings and any(not hangul_re.search(line) for line in ko_headings):
            score -= 2
    return max(0, score)


# ---------------------------------------------------------------------------
# Group 3 — Main quality gate
# ---------------------------------------------------------------------------

def _log_cp_subscores(digest_type: str, persona_label: str, breakdown: dict[str, Any]) -> None:
    """Emit one-line log of NQ-40 Phase 2a CP sub-scores for observability.

    Sub-scores live under breakdown["community_pulse"] (LLM-returned structure).
    Weight=0 during Phase 2a — values don't affect the digest total; the log
    is the primary observation channel for the 2-week window.
    """
    cp = (breakdown or {}).get("community_pulse") or {}
    if not cp:
        return

    def _s(key: str) -> str:
        val = cp.get(key)
        if isinstance(val, dict) and isinstance(val.get("score"), (int, float)):
            return str(int(val["score"]))
        return "n/a"

    logger.info(
        "cp_quality %s/%s: relevance=%s substance=%s fidelity=%s",
        digest_type, persona_label,
        _s("cp_relevance"), _s("cp_substance"), _s("translation_fidelity"),
    )


async def _check_digest_quality(
    personas: dict[str, PersonaOutput],
    digest_type: str,
    classified: list,
    community_summary_map: dict,
    supabase,
    run_id: str,
    cumulative_usage: dict[str, Any],
    frontload: dict[str, Any] | None = None,
    enriched_map: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Score quality of generated digest with body + frontload + deterministic checks."""
    t0 = time.monotonic()
    from services.agents.prompts_news_pipeline import (
        QUALITY_CHECK_RESEARCH_EXPERT, QUALITY_CHECK_RESEARCH_LEARNER,
        QUALITY_CHECK_BUSINESS_EXPERT, QUALITY_CHECK_BUSINESS_LEARNER,
        QUALITY_CHECK_FRONTLOAD,
    )

    expert = personas.get("expert")
    learner = personas.get("learner")
    if not expert or not expert.en:
        logger.warning("Quality check skipped for %s: no expert content", digest_type)
        await _log_stage(
            supabase, run_id, f"quality:{digest_type}", "skipped", t0,
            output_summary="No expert content available",
            post_type=digest_type,
            debug_meta={"quality_score": 0, "skipped": True},
        )
        return 0

    if digest_type == "research":
        expert_prompt = QUALITY_CHECK_RESEARCH_EXPERT
        learner_prompt = QUALITY_CHECK_RESEARCH_LEARNER
    else:
        expert_prompt = QUALITY_CHECK_BUSINESS_EXPERT
        learner_prompt = QUALITY_CHECK_BUSINESS_LEARNER

    client = get_openai_client()
    quality_model = settings.openai_model_reasoning  # gpt-5-mini — nano can't score

    async def _score(prompt: str, content: str, label: str, default_scope: str) -> tuple[int, dict, list[dict[str, str]], dict]:
        max_retries = 2
        for attempt in range(max_retries):
            try:
                resp = await client.chat.completions.create(
                    **build_completion_kwargs(
                        model=quality_model,
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": content[:35000]},
                        ],
                        max_tokens=1500,  # rubric with evidence per sub-score is verbose
                        response_format={"type": "json_object"},
                        service_tier="flex",
                        prompt_cache_key=f"qc-{label}",
                    )
                )
                raw = resp.choices[0].message.content
                if not raw or not raw.strip():
                    logger.warning("Quality check %s attempt %d: empty response", label, attempt + 1)
                    continue
                data = parse_ai_json(raw, label)
                if not data:
                    logger.warning("Quality check %s attempt %d: parse failed", label, attempt + 1)
                    continue

                # v11 rubric: LLM returns nested sub-scores {group: {sub: {evidence, score}}}.
                # Code aggregates to 0-100. All 3 body+frontload prompts ship on this
                # contract post-NP-QUALITY-06 + NQ-37. The data["score"] fallback stays
                # as defense-in-depth — protects against LLM returning legacy single-score
                # format by accident, never reached on a well-formed response.
                score = _aggregate_subscores(data)
                if score == 0 and "score" in data:
                    score = int(data.get("score", 0))

                usage = extract_usage_metrics(resp, quality_model)
                issues = _extract_structured_issues(data.get("issues"), default_scope)
                return score, data, issues, usage
            except Exception as e:
                logger.warning("Quality check %s attempt %d failed: %s", label, attempt + 1, e)
        logger.error("Quality check %s failed after %d attempts", label, max_retries)
        return 0, {}, [], {}

    tasks = [
        _score(
            expert_prompt,
            _build_body_quality_payload("expert", expert),
            f"Quality-{digest_type}-expert",
            "expert_body",
        )
    ]
    if learner and (learner.en or learner.ko):
        tasks.append(
            _score(
                learner_prompt,
                _build_body_quality_payload("learner", learner),
                f"Quality-{digest_type}-learner",
                "learner_body",
            )
        )
    tasks.append(
        _score(
            QUALITY_CHECK_FRONTLOAD,
            _build_frontload_quality_payload(frontload),
            f"Quality-{digest_type}-frontload",
            "frontload",
        )
    )

    results = await asyncio.gather(*tasks)

    expert_score, expert_breakdown, expert_issues, expert_usage = results[0]
    if learner and (learner.en or learner.ko):
        learner_score, learner_breakdown, learner_issues, learner_usage = results[1]
        frontload_score, frontload_breakdown, frontload_issues, frontload_usage = results[2]
    else:
        learner_score, learner_breakdown, learner_issues, learner_usage = (0, {}, [], {})
        frontload_score, frontload_breakdown, frontload_issues, frontload_usage = results[1]

    _log_cp_subscores(digest_type, "expert", expert_breakdown)
    if learner and (learner.en or learner.ko):
        _log_cp_subscores(digest_type, "learner", learner_breakdown)

    structure_score = _compute_structure_score(personas)
    traceability_score = _compute_traceability_score(personas)
    locale_score = _compute_locale_score(personas)
    deterministic_score = structure_score + traceability_score + locale_score

    weighted_expert_body = round(expert_score * 0.2)
    weighted_learner_body = round(learner_score * 0.2) if learner and (learner.en or learner.ko) else 0
    weighted_frontload = round(frontload_score * 0.2)
    llm_score = weighted_expert_body + weighted_learner_body + weighted_frontload

    structural_penalty, structural_warnings = _check_structural_penalties(
        expert, learner, community_summary_map, classified,
    )
    if structural_penalty > 0:
        logger.info("Structural penalties for %s: -%d (%s)", digest_type, structural_penalty, "; ".join(structural_warnings))

    all_issues = expert_issues + learner_issues + frontload_issues
    pre_issue_score = max(0, deterministic_score + llm_score - structural_penalty)
    final_score, issue_penalty, quality_caps_applied = _apply_issue_penalties_and_caps(
        pre_issue_score,
        all_issues,
    )

    merged_quality_usage = merge_usage_metrics(expert_usage, learner_usage) if learner_usage else expert_usage
    merged_quality_usage = merge_usage_metrics(merged_quality_usage, frontload_usage) if frontload_usage else merged_quality_usage

    result = {
        "score": final_score,
        "quality_score": final_score,
        "quality_version": "v2",
        "deterministic_score": deterministic_score,
        "llm_score": llm_score,
        "issue_penalty": issue_penalty,
        "quality_caps_applied": quality_caps_applied,
        "structural_penalty": structural_penalty,
        "structural_warnings": structural_warnings,
        "quality_issues": all_issues,
        "quality_breakdown": {
            "deterministic": {
                "structure": structure_score,
                "traceability": traceability_score,
                "locale": locale_score,
            },
            "llm": {
                "expert_body": weighted_expert_body,
                "learner_body": weighted_learner_body,
                "frontload": weighted_frontload,
            },
            "raw_llm": {
                "expert_body": expert_score,
                "learner_body": learner_score,
                "frontload": frontload_score,
            },
        },
        "expert_breakdown": expert_breakdown.get("subscores", {k: v for k, v in expert_breakdown.items() if k not in {"score", "issues"}}),
        "learner_breakdown": learner_breakdown.get("subscores", {k: v for k, v in learner_breakdown.items() if k not in {"score", "issues"}}),
        "frontload_breakdown": frontload_breakdown.get("subscores", {k: v for k, v in frontload_breakdown.items() if k not in {"score", "issues"}}),
        "news_count": len(classified),
    }

    # Phase 2 — URL strict allowlist validation (cite-check).
    # Allowlist covers EVERY URL the writer was shown:
    #   (1) Every item URL across all classified groups (group.items[*].url)
    #   (2) Every enriched/related URL (enriched_map values) — added post-classify,
    #       used by writer prompt. Without (2), enrichment URLs trigger false positives.
    #   (3) Every CommunityInsight thread URL (hn_url / reddit_url) — Community
    #       Pulse block headers emit `**[Hacker News](thread_url)**` after the
    #       linkifier post-process. Without (3), CP thread URLs trigger false-
    #       positive url_validation_failed flag (see 2026-04-25 fix).
    allowed_items: list[dict[str, str]] = []
    for g in classified:
        for item in (g.items or []):
            if getattr(item, "url", None):
                allowed_items.append({"url": item.url, "title": g.group_title})
    for anchor_url, enriched_list in (enriched_map or {}).items():
        if anchor_url:
            allowed_items.append({"url": anchor_url, "title": "enriched_anchor"})
        for entry in (enriched_list or []):
            url = entry.get("url") if isinstance(entry, dict) else None
            if url:
                allowed_items.append({"url": url, "title": "enriched_related"})
    for insight in (community_summary_map or {}).values():
        hn_url = getattr(insight, "hn_url", None)
        if hn_url:
            allowed_items.append({"url": hn_url, "title": "cp_hn_thread"})
        reddit_url = getattr(insight, "reddit_url", None)
        if reddit_url:
            allowed_items.append({"url": reddit_url, "title": "cp_reddit_thread"})
    fact_pack_for_validation = {"news_items": allowed_items}
    url_validation_failures: list[dict[str, Any]] = []
    for persona_name, persona_output in personas.items():
        if not persona_output:
            continue
        for locale, content in (("en", persona_output.en), ("ko", persona_output.ko)):
            if not content:
                continue
            url_result = validate_citation_urls(content, fact_pack_for_validation)
            if not url_result["valid"]:
                url_validation_failures.append({
                    "persona": persona_name,
                    "locale": locale,
                    "unknown_urls": url_result["unknown_urls"],
                    "citation_count": url_result["citation_count"],
                })

    if url_validation_failures:
        logger.warning(
            "URL validation failed for %s digest: %d persona/locale pairs with unknown URLs",
            digest_type, len(url_validation_failures),
        )
        result["url_validation_failed"] = True
        result["url_validation_failures"] = url_validation_failures
        result["auto_publish_eligible"] = False
    else:
        result["url_validation_failed"] = False

    await _log_stage(
        supabase, run_id, f"quality:{digest_type}", "success", t0,
        output_summary=(
            f"score={final_score}/100 (expert={expert_score}, learner={learner_score}, "
            f"frontload={frontload_score}, deterministic={deterministic_score}, "
            f"issue_penalty=-{issue_penalty}, structural=-{structural_penalty})"
        ),
        usage=merged_quality_usage,
        post_type=digest_type,
        debug_meta=result,
    )

    logger.info(
        "Quality check %s: final=%d/100 (deterministic=%d, llm=%d, issues=-%d, structural=-%d)",
        digest_type, final_score, deterministic_score, llm_score, issue_penalty, structural_penalty,
    )
    return result


# ---------------------------------------------------------------------------
# Group 4 — Blocker / penalty checkers
# ---------------------------------------------------------------------------

def _find_digest_blockers(
    personas: dict[str, PersonaOutput],
    classified: list[ClassifiedGroup] | None = None,
) -> list[str]:
    """Return hard-blocking structural issues that should prevent saving drafts."""
    import re as _re
    from collections import Counter

    hangul_re = _re.compile(r"[\u3131-\u318E\uAC00-\uD7A3]")
    placeholder_re = _re.compile(r"^[-\u2013\u2014:|/·•*~_()\[\]\s]+$")
    blockers: list[str] = []

    for persona_name, output in personas.items():
        for locale, content in (("en", output.en), ("ko", output.ko)):
            if not content:
                continue
            for raw_line in content.splitlines():
                if not raw_line.startswith("### "):
                    continue
                heading = raw_line[4:].strip()
                if not heading or placeholder_re.fullmatch(heading):
                    blockers.append(
                        f"{persona_name} {locale}: placeholder `###` heading `{raw_line.strip()}`"
                    )
                    continue
                if locale == "en" and hangul_re.search(heading):
                    blockers.append(
                        f"{persona_name} {locale}: Hangul in EN `###` heading `{raw_line.strip()}`"
                    )

        if classified and output.en and output.ko:
            en_items = _extract_digest_items(output.en)
            ko_items = _extract_digest_items(output.ko)
            if len(en_items) != len(ko_items):
                blockers.append(
                    f"{persona_name}: locale parity item count mismatch EN={len(en_items)} KO={len(ko_items)}"
                )
                continue

            en_group_indexes, en_unmapped = _map_digest_items_to_group_indexes(output.en, classified)
            ko_group_indexes, ko_unmapped = _map_digest_items_to_group_indexes(output.ko, classified)
            if not en_unmapped and not ko_unmapped:
                if Counter(en_group_indexes) != Counter(ko_group_indexes):
                    blockers.append(
                        f"{persona_name}: locale parity story set mismatch EN={sorted(en_group_indexes)} KO={sorted(ko_group_indexes)}"
                    )

    return blockers


def _check_structural_penalties(
    expert: PersonaOutput,
    learner: PersonaOutput | None,
    community_summary_map: dict,
    classified: list,
) -> tuple[int, list[str]]:
    """Check structural rule violations in Writer output. Returns (penalty, warnings).

    Runs AFTER _strip_empty_sections post-processing.
    Penalty is subtracted from LLM quality score.
    """
    import re as _re
    penalty = 0
    warnings: list[str] = []

    # Check 1: CP data provided FOR THIS DIGEST but CP section missing (-15)
    # Only check insights that match URLs in this digest's classified groups
    digest_urls = {url for group in classified for url in (group.urls if hasattr(group, 'urls') else [])}
    has_cp_data = any(
        (ins.quotes or ins.key_point) and url in digest_urls
        for url, ins in community_summary_map.items()
    ) if community_summary_map else False

    if has_cp_data:
        for persona_name, output in [("expert", expert), ("learner", learner)]:
            if not output:
                continue
            for locale, content in [("en", output.en), ("ko", output.ko)]:
                if not content:
                    continue
                cp_present = "## Community Pulse" in content or "## 커뮤니티 반응" in content
                if not cp_present:
                    penalty += 15
                    warnings.append(f"CP data provided but missing in {persona_name} {locale}")

    # Check 1b: EN has CP but KO doesn't (-10)
    for persona_name, output in [("expert", expert), ("learner", learner)]:
        if not output or not output.en or not output.ko:
            continue
        en_has_cp = "## Community Pulse" in output.en
        ko_has_cp = "## 커뮤니티 반응" in output.ko or "## Community Pulse" in output.ko
        if en_has_cp and not ko_has_cp:
            penalty += 10
            warnings.append(f"EN has CP but KO missing in {persona_name}")

    # Check 1c: Leaked placeholder literal `[EN quote]` / `[KO quote]` (-10 per occurrence, max -20)
    # Acts as runtime safety net in case _clean_writer_output regex misses a variant
    for persona_name, output in [("expert", expert), ("learner", learner)]:
        if not output:
            continue
        for locale, content in [("en", output.en), ("ko", output.ko)]:
            if not content:
                continue
            leaks = len(_re.findall(r"\[(?:EN|KO)\s*quote\]", content, _re.IGNORECASE))
            if leaks:
                inc = min(leaks * 10, 20)
                penalty += inc
                warnings.append(f"CP leaked {leaks} placeholder literal(s) in {persona_name} {locale}")

    # Check 2: CP exists as ###/#### instead of ## (-5)
    for persona_name, output in [("expert", expert), ("learner", learner)]:
        if not output:
            continue
        for locale, content in [("en", output.en), ("ko", output.ko)]:
            if not content:
                continue
            if _re.search(r"^#{3,4}\s*(Community Pulse|커뮤니티 반응)", content, _re.MULTILINE):
                penalty += 5
                warnings.append(f"CP uses ###/#### instead of ## in {persona_name} {locale}")

    # Check 3: EN/KO section count mismatch (-5)
    for persona_name, output in [("expert", expert), ("learner", learner)]:
        if not output or not output.en or not output.ko:
            continue
        en_sections = [line for line in output.en.split("\n") if line.strip().startswith("## ")]
        ko_sections = [line for line in output.ko.split("\n") if line.strip().startswith("## ")]
        diff = abs(len(en_sections) - len(ko_sections))
        if diff >= 2:
            penalty += 5
            warnings.append(f"EN/KO section mismatch in {persona_name}: EN={len(en_sections)} KO={len(ko_sections)}")

    # Check 4: Empty citations [](URL) (-5)
    for persona_name, output in [("expert", expert), ("learner", learner)]:
        if not output:
            continue
        for locale, content in [("en", output.en), ("ko", output.ko)]:
            if not content:
                continue
            if _re.findall(r"\[\]\(https?://", content):
                penalty += 5
                warnings.append(f"Empty citations [](URL) in {persona_name} {locale}")

    # Check 5: Supporting items with < 3 paragraphs (-5 each, max -10)
    short_count = 0
    for output in [expert, learner]:
        if not output or not output.en:
            continue
        items = _re.split(r"^### ", output.en, flags=_re.MULTILINE)
        for item in items[1:]:
            if "[LEAD]" in item or "[SUPPORTING]" not in item:
                continue
            paragraphs = [p.strip() for p in item.split("\n\n") if p.strip() and not p.strip().startswith("#")]
            if len(paragraphs) < 3:
                short_count += 1
    if short_count > 0:
        p = min(short_count * 5, 10)
        penalty += p
        warnings.append(f"{short_count} supporting item(s) have < 3 paragraphs")

    # Check 6: ### heading has body stuck to it (title-only rule violation, -5 each, max -15).
    # A well-formed `### Title` line should be under ~120 chars for most news items.
    # Longer lines almost always indicate body text glued to the heading.
    for persona_name, output in [("expert", expert), ("learner", learner)]:
        if not output:
            continue
        for locale, content in [("en", output.en), ("ko", output.ko)]:
            if not content:
                continue
            long_headings = [
                line for line in content.split("\n")
                if line.startswith("### ") and len(line) > 140
            ]
            if long_headings:
                inc = min(len(long_headings) * 5, 15)
                penalty += inc
                warnings.append(
                    f"{len(long_headings)} over-long `###` heading(s) (body stuck to title?) in {persona_name} {locale}"
                )

    # Check 7: legacy One-Line Summary hard cap disabled; synthesis may run longer.
    # KO: ≤60 Hangul chars (excluding whitespace). EN: ≤15 words.
    def _extract_one_liner(content: str, heading: str) -> str:
        match = _re.search(
            rf"^##\s*{_re.escape(heading)}\s*\n+(.+?)(?:\n|$)",
            content,
            _re.MULTILINE,
        )
        return match.group(1).strip() if match else ""

    for persona_name, output in [("expert", expert), ("learner", learner)]:
        if not output:
            continue
        if False and output.ko:
            ko_line = _extract_one_liner(output.ko, "한 줄 요약")
            ko_len = len(_re.sub(r"\s+", "", ko_line))
            if ko_len > 60:
                penalty += 3
                warnings.append(
                    f"한 줄 요약 too long ({ko_len} chars > 60) in {persona_name} ko"
                )
        if False and output.en:
            en_line = _extract_one_liner(output.en, "One-Line Summary")
            en_words = len(en_line.split()) if en_line else 0
            if en_words > 15:
                penalty += 3
                warnings.append(
                    f"One-Line Summary too long ({en_words} words > 15) in {persona_name} en"
                )

    # Check 8: KO ### heading with zero Hangul (-5 each, max -15)
    _hangul_re = _re.compile(r"[\uAC00-\uD7AF]")
    for persona_name, output in [("expert", expert), ("learner", learner)]:
        if not output or not output.ko:
            continue
        en_only_count = 0
        for line in output.ko.split("\n"):
            if line.startswith("### ") and not _hangul_re.search(line):
                en_only_count += 1
        if en_only_count:
            inc = min(en_only_count * 5, 15)
            penalty += inc
            warnings.append(
                f"{en_only_count} English-only `###` heading(s) in {persona_name} ko"
            )

    return min(penalty, 40), warnings


# ---------------------------------------------------------------------------
# Phase 2 — URL Strict Allowlist Validation
# ---------------------------------------------------------------------------

# Citation pattern: [N](URL) where N is digits and URL starts with http
_CITATION_RE = re.compile(r"\[(\d+)\]\((https?://[^\s\)]+)\)")

# Tracking params to strip during URL normalization
_TRACKING_PARAM_PREFIXES = ("utm_",)
_TRACKING_PARAM_NAMES = frozenset({
    "fbclid", "gclid", "msclkid", "ref", "referrer", "source",
    "share", "share_id", "src", "feature", "campaign",
})


def _normalize_url(url: str) -> str:
    """Normalize URL for citation comparison: scheme, trailing slash, tracking params, fragment."""
    try:
        parsed = urlparse(url.strip())
    except (ValueError, AttributeError):
        return url

    # Force https for comparison (treat http and https as same)
    scheme = "https" if parsed.scheme in ("http", "https") else parsed.scheme

    # Strip trailing slash from path
    path = parsed.path.rstrip("/") or "/"

    # Filter query params: drop tracking
    query_params = [
        (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if not k.lower().startswith(_TRACKING_PARAM_PREFIXES)
        and k.lower() not in _TRACKING_PARAM_NAMES
    ]
    query = urlencode(query_params)

    # Drop fragment
    fragment = ""

    return urlunparse((scheme, parsed.netloc.lower(), path, parsed.params, query, fragment))


async def _validate_urls_live(
    urls,
    timeout: float = 3.0,
    max_concurrent: int = 20,
) -> tuple[set[str], list[dict]]:
    """HEAD-check URLs in parallel. Returns (live_urls, drop_records).

    Complements validate_citation_urls (structural allowlist check) by
    adding liveness verification: does this URL actually resolve?

    Drops on:
    - 404, 410 (definitively gone)
    - Connect error / DNS failure / timeout

    Keeps on (benefit of the doubt — don't punish edge cases):
    - 2xx / 3xx (success or redirect — including cross-domain redirects,
      since brand TLDs like .google redirect between blog.google ↔
      deepmind.google as normal operation; content-farm escape is
      already covered by _classify_source_meta tier/kind filters upstream)
    - 403 (bot blocking — site is alive)
    - 405 (Method Not Allowed — site doesn't support HEAD)
    - 5xx (transient server error)
    - Other 4xx not listed above
    - Any unexpected exception (network infra issue — fail open)

    On infrastructure failure for ALL URLs (e.g., no network), returns the
    input set unchanged to avoid blocking the pipeline.
    """
    import httpx  # imported here so module-level cost stays zero

    url_list = list(urls) if not isinstance(urls, list) else urls
    if not url_list:
        return set(), []

    live: set[str] = set()
    drops: list[dict] = []
    sem = asyncio.Semaphore(max_concurrent)
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; 0to1log/1.0; +https://0to1log.com)",
    }

    async def _check(url: str) -> None:
        async with sem:
            try:
                async with httpx.AsyncClient(
                    timeout=timeout,
                    follow_redirects=True,
                    headers=headers,
                ) as client:
                    resp = await client.head(url)
                    if resp.status_code in (404, 410):
                        drops.append({"url": url, "reason": f"HTTP {resp.status_code}"})
                        return
                    live.add(url)
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.PoolTimeout):
                drops.append({"url": url, "reason": "timeout/connect error"})
            except Exception as e:
                # Fail open on any other exception — don't punish for edge cases
                logger.debug("URL liveness check exception for %s: %s", url, e)
                live.add(url)

    t0 = time.monotonic()
    try:
        await asyncio.gather(*[_check(u) for u in url_list])
    except Exception as e:
        # Network infra failure — return input unchanged
        logger.warning("URL liveness check failed globally: %s. Returning all URLs unchanged.", e)
        return set(url_list), []

    elapsed = time.monotonic() - t0
    logger.info(
        "URL liveness: %d/%d live, %d dropped in %.2fs",
        len(live), len(url_list), len(drops), elapsed,
    )
    return live, drops


def validate_citation_urls(body: str, fact_pack: dict) -> dict:
    """Verify all [N](URL) citations in body refer to URLs in fact_pack.news_items.

    Returns dict with:
      - valid: bool
      - unknown_urls: list[str] — citations that don't match any allowed URL
      - citation_count: int — number of unique URLs cited (after dedup)
      - allowed_count: int — number of URLs in fact_pack.news_items

    Bodies with zero citations always pass (e.g., One-Line Summary section).
    URL comparison is normalized: scheme/trailing-slash/tracking-params/fragment stripped.
    """
    if not body:
        return {"valid": True, "unknown_urls": [], "citation_count": 0, "allowed_count": 0}

    # Build allowed set from fact_pack.news_items[*].url
    news_items = (fact_pack or {}).get("news_items") or []
    allowed = {
        _normalize_url(item["url"])
        for item in news_items
        if isinstance(item, dict) and item.get("url")
    }

    # Extract all citations and dedup by normalized URL
    cited_raw = [m.group(2) for m in _CITATION_RE.finditer(body)]
    cited_norm = {_normalize_url(u) for u in cited_raw}

    if not cited_norm:
        return {"valid": True, "unknown_urls": [], "citation_count": 0, "allowed_count": len(allowed)}

    unknown = sorted(cited_norm - allowed)
    return {
        "valid": len(unknown) == 0,
        "unknown_urls": unknown,
        "citation_count": len(cited_norm),
        "allowed_count": len(allowed),
    }


# ---------------------------------------------------------------------------
# Group 6 — Weekly quality scoring
# ---------------------------------------------------------------------------

async def _check_weekly_quality(
    content_expert_en: str,
    content_learner_en: str,
    content_expert_ko: str,
    content_learner_ko: str,
    source_urls: list[str],
    supabase,
    run_id: str,
    cumulative_usage: dict[str, Any],
) -> dict[str, Any]:
    """Score quality of generated weekly digest."""
    t0 = time.monotonic()
    from services.agents.prompts_news_pipeline import (
        QUALITY_CHECK_WEEKLY_EXPERT, QUALITY_CHECK_WEEKLY_LEARNER,
    )

    if not content_expert_en:
        logger.warning("Weekly quality check skipped: no expert EN content")
        await _log_stage(
            supabase, run_id, "weekly:quality", "skipped", t0,
            output_summary="No expert content", post_type="weekly",
        )
        return {"quality_score": 0, "quality_flags": ["no_expert_content"]}

    client = get_openai_client()
    model = settings.openai_model_reasoning  # gpt-5-mini — match daily quality
    issues_all: list[str] = []
    structured_issues: list[dict[str, str]] = []
    llm_scores: list[int] = []
    # Raw parsed data kept at function scope so we can surface sub-scores in
    # the return dict — mirrors daily's `expert_breakdown`/`learner_breakdown`
    # so the admin QualityPanel can render weekly the same as daily.
    expert_data: dict[str, Any] = {}
    learner_data: dict[str, Any] = {}
    # Usage dicts hoisted to function scope so the final _log_stage can merge
    # them into `merged_quality_usage` even if one try-block failed. Matches
    # daily's pattern in _check_digest_quality where merged_quality_usage is
    # passed to _log_stage so pipeline_logs.cost_usd gets populated.
    expert_usage: dict[str, Any] = {}
    learner_usage: dict[str, Any] = {}

    # Expert quality check
    expert_input = f"## English Expert\n\n{content_expert_en}\n\n## Korean Expert\n\n{content_expert_ko}"
    try:
        async def _weekly_qc_expert_call() -> Any:
            return await asyncio.wait_for(
                client.chat.completions.create(
                    **build_completion_kwargs(
                        model,
                        messages=[
                            {"role": "system", "content": QUALITY_CHECK_WEEKLY_EXPERT},
                            {"role": "user", "content": expert_input},
                        ],
                        response_format={"type": "json_object"},
                        max_tokens=2000,
                        service_tier="flex",
                        prompt_cache_key="qc-weekly-expert",
                    )
                ),
                timeout=120,
            )

        expert_resp = await with_flex_retry(_weekly_qc_expert_call)
        expert_raw = expert_resp.choices[0].message.content or ""
        expert_usage = extract_usage_metrics(expert_resp, model)
        cumulative_usage.update(merge_usage_metrics(cumulative_usage, expert_usage))
        expert_data = parse_ai_json(expert_raw, "weekly-quality-expert")
        # v2 rubric: code aggregates sub-scores. Fall back to data["total_score"]
        # (legacy format) or data["score"] for safety.
        expert_score = _aggregate_subscores(expert_data)
        if expert_score == 0:
            expert_score = int(expert_data.get("total_score") or expert_data.get("score") or 0)
        llm_scores.append(expert_score)
        expert_top_issues = expert_data.get("issues") or []
        if expert_top_issues:
            expert_issues = _extract_structured_issues(expert_top_issues, "expert_body")
            structured_issues.extend(expert_issues)
            for i in expert_issues:
                issues_all.append(f"expert:{i.get('category', 'unknown')}:{i.get('message', '')}")
        else:
            # Legacy fallback: flatten per-subcategory strings (no penalty structure available).
            for cat in ["section_completeness", "source_quality", "depth_synthesis", "language_tone"]:
                for issue in (expert_data.get(cat, {}).get("issues") or []):
                    issues_all.append(f"expert:{cat}:{issue}")
    except Exception as e:
        logger.warning("Weekly expert quality check failed: %s", e)
        expert_score = 0

    # Learner quality check
    if content_learner_en:
        learner_input = f"## English Learner\n\n{content_learner_en}\n\n## Korean Learner\n\n{content_learner_ko}"
        try:
            async def _weekly_qc_learner_call() -> Any:
                return await asyncio.wait_for(
                    client.chat.completions.create(
                        **build_completion_kwargs(
                            model,
                            messages=[
                                {"role": "system", "content": QUALITY_CHECK_WEEKLY_LEARNER},
                                {"role": "user", "content": learner_input},
                            ],
                            response_format={"type": "json_object"},
                            max_tokens=2000,
                            service_tier="flex",
                            prompt_cache_key="qc-weekly-learner",
                        )
                    ),
                    timeout=120,
                )

            learner_resp = await with_flex_retry(_weekly_qc_learner_call)
            learner_raw = learner_resp.choices[0].message.content or ""
            learner_usage = extract_usage_metrics(learner_resp, model)
            cumulative_usage.update(merge_usage_metrics(cumulative_usage, learner_usage))
            learner_data = parse_ai_json(learner_raw, "weekly-quality-learner")
            learner_score = _aggregate_subscores(learner_data)
            if learner_score == 0:
                learner_score = int(learner_data.get("total_score") or learner_data.get("score") or 0)
            llm_scores.append(learner_score)
            learner_top_issues = learner_data.get("issues") or []
            if learner_top_issues:
                learner_issues = _extract_structured_issues(learner_top_issues, "learner_body")
                structured_issues.extend(learner_issues)
                for i in learner_issues:
                    issues_all.append(f"learner:{i.get('category', 'unknown')}:{i.get('message', '')}")
            else:
                for cat in ["section_completeness", "source_quality", "depth_accessibility", "language_tone"]:
                    for issue in (learner_data.get(cat, {}).get("issues") or []):
                        issues_all.append(f"learner:{cat}:{issue}")
        except Exception as e:
            logger.warning("Weekly learner quality check failed: %s", e)

    # URL validation
    url_penalty = 0
    if source_urls:
        fact_pack_for_validation = {"news_items": [{"url": u} for u in source_urls]}
        url_result = validate_citation_urls(content_expert_en, fact_pack_for_validation)
        hallucinated = len(url_result.get("unknown_urls", []))
        if hallucinated > 0:
            url_penalty = min(hallucinated * 3, 15)
            issues_all.append(f"url_validation:{hallucinated} hallucinated URLs (-{url_penalty})")

    # Structural penalties
    structural_penalty = 0
    structural_warnings: list[str] = []
    if len(content_expert_en) < 10000:
        structural_penalty += 5
        structural_warnings.append("expert_en_short")
    if content_expert_ko and len(content_expert_ko) < 6000:
        structural_penalty += 5
        structural_warnings.append("expert_ko_short")

    # v2 scoring: deterministic (0-40) + weighted LLM (0-60) — matches daily pattern.
    structure_score = _compute_weekly_structure_score(
        content_expert_en, content_expert_ko, content_learner_en, content_learner_ko,
    )
    traceability_score = _compute_weekly_traceability_score(
        content_expert_en, content_expert_ko, content_learner_en, content_learner_ko,
    )
    locale_score = _compute_weekly_locale_score(
        content_expert_en, content_expert_ko, content_learner_en, content_learner_ko,
    )
    deterministic_score = structure_score + traceability_score + locale_score

    llm_avg = round(sum(llm_scores) / len(llm_scores)) if llm_scores else 0
    weighted_llm = round(llm_avg * 0.6)
    pre_issue_score = max(0, deterministic_score + weighted_llm - url_penalty - structural_penalty)

    # Issue penalty + score caps (daily parity). Requires structured issues
    # from v2-format LLM output. Legacy per-subcat flat strings result in
    # empty structured_issues → no penalty applied (0 impact).
    final_score, issue_penalty, quality_caps_applied = _apply_issue_penalties_and_caps(
        pre_issue_score, structured_issues,
    )

    quality_flags = []
    if url_penalty:
        quality_flags.append("url_hallucination")
    if structural_warnings:
        quality_flags.extend(structural_warnings)
    if quality_caps_applied:
        quality_flags.extend(quality_caps_applied)

    # URL validation gate (daily parity): hallucinated URLs block auto-publish
    # even if score passes threshold. Matches pipeline_quality.py:509.
    url_validation_failed = hallucinated > 0 if source_urls else False
    if url_validation_failed:
        quality_flags.append("url_validation_failed")

    auto_publish_eligible = (
        final_score >= settings.auto_publish_threshold
        and not url_validation_failed
    )

    quality_breakdown = {
        "deterministic": {
            "structure": structure_score,
            "traceability": traceability_score,
            "locale": locale_score,
            "total": deterministic_score,
        },
        "llm": {
            "weighted": weighted_llm,
            "raw_avg": llm_avg,
        },
        "penalties": {
            "url": url_penalty,
            "structural": structural_penalty,
            "issue": issue_penalty,
        },
        "caps_applied": quality_caps_applied,
        "issue_count": len(structured_issues),
    }

    logger.info(
        "Weekly quality: final=%d (det=%d, llm_weighted=%d, pre_issue=%d, "
        "url=-%d, struct=-%d, issue=-%d, caps=%s), eligible=%s (url_gate_blocked=%s)",
        final_score, deterministic_score, weighted_llm, pre_issue_score,
        url_penalty, structural_penalty, issue_penalty, quality_caps_applied,
        auto_publish_eligible, url_validation_failed,
    )

    # Merge expert+learner usage so _log_stage populates pipeline_logs.cost_usd
    # (daily parity — see _check_digest_quality:630). Stage name uses
    # `weekly:` prefix so admin pipeline-analytics's `pipeline_type LIKE 'weekly:%'`
    # filter picks it up; historical rows named `quality:weekly` predate this fix.
    merged_quality_usage = merge_usage_metrics(expert_usage, learner_usage)
    await _log_stage(
        supabase, run_id, "weekly:quality", "success", t0,
        output_summary=(
            f"score={final_score} (det={deterministic_score} [s={structure_score},"
            f"t={traceability_score},l={locale_score}], llm_w={weighted_llm}, "
            f"url=-{url_penalty}, struct=-{structural_penalty})"
        ),
        usage=merged_quality_usage,
        post_type="weekly",
        debug_meta={
            "quality_score": final_score,
            "quality_breakdown": quality_breakdown,
            "quality_version": "v2",
            "issues": issues_all[:20],
        },
    )

    # v11 sub-score surfaces — mirror daily's expert_breakdown/learner_breakdown
    # so the admin QualityPanel can render weekly the same as daily.
    # Filter out non-subscore keys ('issues', 'score', 'subscores') the same way
    # daily does at pipeline_quality.py:578-579.
    def _extract_subscores(data: dict) -> dict:
        if not data:
            return {}
        if "subscores" in data and isinstance(data["subscores"], dict):
            return data["subscores"]
        return {k: v for k, v in data.items() if k not in {"score", "issues", "total_score"}}

    return {
        "quality_score": final_score,
        "quality_flags": quality_flags,
        "content_analysis": {"issues": issues_all[:30]},
        "auto_publish_eligible": auto_publish_eligible,
        "quality_breakdown": quality_breakdown,
        "quality_version": "v2",
        "expert_breakdown": _extract_subscores(expert_data),
        "learner_breakdown": _extract_subscores(learner_data),
        "quality_issues": structured_issues,
        "structural_penalty": structural_penalty,
        "structural_warnings": structural_warnings,
        "quality_caps_applied": quality_caps_applied,
        "url_validation_failed": url_validation_failed,
        "url_validation_failures": (
            [{"unknown_urls": url_result.get("unknown_urls", [])}]
            if source_urls and hallucinated > 0 else []
        ),
    }

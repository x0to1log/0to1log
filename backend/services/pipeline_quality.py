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

from core.config import settings
from models.news_pipeline import ClassifiedGroup, PersonaOutput
from services.agents.client import (
    build_completion_kwargs,
    extract_usage_metrics,
    get_openai_client,
    merge_usage_metrics,
    parse_ai_json,
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
    """Build a bilingual body-scoring payload for one persona."""
    return (
        f"Persona: {persona_name}\n\n"
        "=== EN ===\n"
        f"{persona_output.en.strip()}\n\n"
        "=== KO ===\n"
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
                caps.append((89, "frontload_overclaim_cap_89"))
            if category == "locale" or scope == "ko":
                caps.append((89, "locale_quality_cap_89"))
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

async def _check_digest_quality(
    personas: dict[str, PersonaOutput],
    digest_type: str,
    classified: list,
    community_summary_map: dict,
    supabase,
    run_id: str,
    cumulative_usage: dict[str, Any],
    frontload: dict[str, Any] | None = None,
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
                            {"role": "user", "content": content[:20000]},
                        ],
                        max_tokens=500,
                        temperature=0,
                        response_format={"type": "json_object"},
                    )
                )
                raw = resp.choices[0].message.content
                if not raw or not raw.strip():
                    logger.warning("Quality check %s attempt %d: empty response", label, attempt + 1)
                    continue
                data = parse_ai_json(raw, label)
                if not data or "score" not in data:
                    logger.warning("Quality check %s attempt %d: no score in response", label, attempt + 1)
                    continue
                usage = extract_usage_metrics(resp, quality_model)
                issues = _extract_structured_issues(data.get("issues"), default_scope)
                return int(data.get("score", 0)), data, issues, usage
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

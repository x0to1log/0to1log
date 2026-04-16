"""Digest generation for daily news pipeline.

Contains:
  - _generate_digest: main per-persona digest generator (calls LLM, builds JSON output)
  - Content cleaners: _strip_empty_sections, _fix_bold_spacing, _clean_writer_output
  - Item extractors: _extract_digest_items, _map_digest_items_to_group_indexes

Extracted from pipeline.py during 2026-04-15 Phase 1.
External callers should still import from services.pipeline (re-exported).
"""
import asyncio
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from core.config import settings
from models.news_pipeline import (
    ClassifiedGroup,
    CommunityInsight,
    PersonaOutput,
)
from services.agents.client import (
    compat_create_kwargs,
    extract_usage_metrics,
    get_openai_client,
    merge_usage_metrics,
    parse_ai_json,
)
from services.agents.prompts_news_pipeline import get_digest_prompt

# Helpers that remain in pipeline.py — safe to import because they are defined
# near the top of pipeline.py (before the re-export block at the bottom).
from services.pipeline import (  # type: ignore[attr-defined]
    _dedup_source_cards,
    _fill_source_titles,
    _log_stage,
    _renumber_citations,
    _trim,
)

# NOTE: _check_digest_quality and _find_digest_blockers are imported lazily
# inside _generate_digest to avoid a circular import (pipeline_quality imports
# _extract_digest_items from this module).

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Content cleaners
# ---------------------------------------------------------------------------

def _strip_empty_sections(content: str) -> str:
    """Remove ## sections that have a heading but no content (Rule 11 compliance).

    Detects patterns like:
      ## LLM & SOTA Models\n\n## Open Source & Repos  (empty section)
      ## Section Title\n\n  (trailing empty section)
    """
    import re as _re
    # Split into sections by ## headings
    parts = _re.split(r'(^## .+$)', content, flags=_re.MULTILINE)
    result = []
    i = 0
    while i < len(parts):
        if parts[i].startswith("## "):
            heading = parts[i]
            body = parts[i + 1] if i + 1 < len(parts) else ""
            # Check if body has actual content (not just whitespace)
            if body.strip():
                result.append(heading)
                result.append(body)
            else:
                logger.debug("Stripped empty section: %s", heading.strip())
            i += 2
        else:
            result.append(parts[i])
            i += 1
    return "".join(result)


def _fix_bold_spacing(content: str) -> str:
    """Fix broken markdown bold: '**text **' → '**text**'."""
    import re as _re
    return _re.sub(r"\*\*(.+?)\s+\*\*", r"**\1**", content)


def _clean_writer_output(content: str) -> str:
    """Post-process Writer output: strip empty sections, fix bold, remove [LEAD] tags."""
    import re as _re
    content = _strip_empty_sections(content)
    content = _fix_bold_spacing(content)
    # Remove [LEAD]/[SUPPORTING] tags and (Lead)/(Supporting) from headings
    content = _re.sub(r"\s*\[LEAD\]\s*", " ", content)
    content = _re.sub(r"\s*\[SUPPORTING\]\s*", " ", content)
    content = _re.sub(r"\s*\(Lead\)\s*", "", content, flags=_re.IGNORECASE)
    content = _re.sub(r"\s*\(Supporting\)\s*", "", content, flags=_re.IGNORECASE)
    # Also catch Korean translation of LEAD/SUPPORTING
    content = _re.sub(r"\s*\(리드\)\s*", "", content)
    content = _re.sub(r"\s*\(서포팅\)\s*", "", content)
    # [BODY] marker → blank line (legacy backward compat; skeletons no longer use [BODY])
    content = content.replace("[BODY]", "\n")
    # Regex fallback: if a ### line still has body text stuck to it (LLM dropped
    # the newline entirely), try to split at the first ". " (period + space)
    # followed by a capital letter or Hangul syllable. Titles rarely end with
    # a period, so this is a strong boundary signal.
    def _split_heading_body(match: _re.Match) -> str:
        head = match.group(1)  # "### " prefix
        line = match.group(2)  # rest of the heading line
        # Try to find a sentence boundary inside the line
        m = _re.search(r'([^.!?]+?[.!?])\s+([A-Z\u3131-\uD7A3])', line)
        if m:
            title_part = line[:m.end(1)]
            body_part = line[m.end(1):].lstrip()
            return f"{head}{title_part}\n\n{body_part}"
        return match.group(0)
    # Apply only to ### lines longer than 120 chars (heuristic: normal titles
    # are rarely that long, and this avoids false-positives on legitimate titles)
    content = _re.sub(r"^(### )([^\n]{120,})$", _split_heading_body, content, flags=_re.MULTILINE)
    # Also: if a ### line is followed DIRECTLY by a non-blank line (no blank line
    # separator), insert a blank line. This catches the milder regression where
    # LLM has title on its own line but no blank line before body.
    content = _re.sub(r"^(### [^\n]+)\n(?!\n|### |## |- |\d+\. )", r"\1\n\n", content, flags=_re.MULTILINE)
    # Remove Quote (EN)/Quote (KO) labels mistakenly used as attribution
    content = _re.sub(r"—\s*Quote\s*\((?:EN|KO)\)", "", content)
    # Remove leaked `[EN quote]` / `[KO quote]` placeholder literals
    # First: drop entire blockquote lines that contain only the placeholder
    # (pattern: `> "[EN quote]"` followed by `> — Source`)
    content = _re.sub(
        r'>\s*"?\[(?:EN|KO)\s*quote\]"?\s*\n(?:>\s*—[^\n]*\n?)?',
        "", content, flags=_re.IGNORECASE,
    )
    # Fallback: any remaining literal occurrences inside prose
    content = _re.sub(r'"?\[(?:EN|KO)\s*quote\]"?', "", content, flags=_re.IGNORECASE)
    return content


# ---------------------------------------------------------------------------
# Item extractors
# ---------------------------------------------------------------------------

def _extract_digest_items(content: str) -> list[tuple[str, set[str]]]:
    """Extract digest `###` items and the URLs cited inside each item."""
    import re as _re

    citation_re = _re.compile(r"\[\d+\]\((https?://[^)]+)\)")
    items: list[tuple[str, set[str]]] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    def _flush() -> None:
        nonlocal current_heading, current_lines
        if current_heading is None:
            return
        items.append((current_heading, set(citation_re.findall("\n".join(current_lines)))))
        current_heading = None
        current_lines = []

    for line in content.splitlines():
        if line.startswith("### "):
            _flush()
            current_heading = line[4:].strip()
            current_lines = []
            continue
        if current_heading is not None:
            if line.startswith("## "):
                _flush()
                continue
            current_lines.append(line)

    _flush()
    return items


def _map_digest_items_to_group_indexes(
    content: str, classified: list[ClassifiedGroup],
) -> tuple[list[int], list[str]]:
    """Map digest items to classified groups by overlapping cited primary URLs."""
    group_url_sets = [set(group.urls) for group in classified]
    mapped_indexes: list[int] = []
    unmapped_headings: list[str] = []

    for heading, cited_urls in _extract_digest_items(content):
        best_index = -1
        best_overlap = 0
        for idx, group_urls in enumerate(group_url_sets):
            overlap = len(cited_urls & group_urls)
            if overlap > best_overlap:
                best_overlap = overlap
                best_index = idx
        if best_index >= 0 and best_overlap > 0:
            mapped_indexes.append(best_index)
        else:
            unmapped_headings.append(heading)

    return mapped_indexes, unmapped_headings


# ---------------------------------------------------------------------------
# Main digest generator
# ---------------------------------------------------------------------------

async def _generate_digest(
    classified: list[ClassifiedGroup],
    digest_type: str,
    batch_id: str,
    handbook_slugs: list[str],
    raw_content_map: dict[str, str],
    community_summary_map: dict[str, "CommunityInsight"],
    supabase,
    run_id: str,
    enriched_map: dict[str, list[dict]] | None = None,
    auto_publish: bool = False,
) -> tuple[int, list[str], dict[str, Any]]:
    """Generate a daily digest post for one category (research or business).

    Creates 2 persona versions (expert/learner) × 2 locales (en/ko).
    Returns (posts_created, errors, usage).
    """
    errors: list[str] = []
    cumulative_usage: dict[str, Any] = {}
    posts_created = 0

    if not classified:
        return 0, [], {}

    def _normalize_source_url(url: str) -> str:
        return (url or "").strip().rstrip("/")

    def _source_sort_key(meta: dict[str, Any]) -> tuple[int, int, int, str]:
        tier_rank = {"primary": 0, "secondary": 1}
        kind_rank = {
            "official_site": 0,
            "paper": 1,
            "official_repo": 2,
            "official_platform_asset": 3,
            "registry": 4,
            "media": 5,
            "analysis": 6,
            "community": 7,
        }
        confidence_rank = {"high": 0, "medium": 1, "low": 2}
        return (
            tier_rank.get((meta.get("source_tier") or "").lower(), 9),
            kind_rank.get((meta.get("source_kind") or "").lower(), 9),
            confidence_rank.get((meta.get("source_confidence") or "").lower(), 9),
            _normalize_source_url(meta.get("url", "")),
        )

    def _format_source_header(index: int, source_url: str, meta: dict[str, Any]) -> str:
        tier = (meta.get("source_tier") or "").upper()
        kind = meta.get("source_kind") or ""
        confidence = meta.get("source_confidence") or ""
        if tier and kind and confidence:
            return f"Source {index} [{tier} / {kind} / {confidence}]: {source_url}"
        return f"Source {index}: {source_url}"

    # Build user prompt from classified groups
    _enriched = enriched_map or {}
    news_items = []
    for group in classified:
        # Multi-source: use enriched sources (from merge or Exa), else raw_content
        sources = _enriched.get(group.primary_url)
        if sources:
            ordered_sources = []
            seen_source_urls: set[str] = set()
            for src in sorted(sources, key=_source_sort_key):
                normalized_url = _normalize_source_url(src.get("url", ""))
                if normalized_url and normalized_url in seen_source_urls:
                    continue
                if normalized_url:
                    seen_source_urls.add(normalized_url)
                ordered_sources.append(src)
            sources = ordered_sources
            best_content = max((s.get("content", "") for s in sources), key=len)
            if len(best_content.strip()) < 80:
                logger.info(
                    "Skipping filler group '%s' — best source too short (%d chars)",
                    group.group_title[:60], len(best_content.strip()),
                )
                continue
            source_blocks = []
            for i, src in enumerate(sources, 1):
                content = src.get("content", "")
                if len(content.strip()) < 40:
                    continue
                source_blocks.append(
                    f"{_format_source_header(i, src['url'], src)}\n{content[:12000]}"
                )
            body_block = "\n\n".join(source_blocks)
        else:
            # Fallback: assemble from raw_content_map for each item in group
            source_blocks = []
            for i, item in enumerate(group.items, 1):
                content = raw_content_map.get(item.url, "")
                if len(content.strip()) < 40:
                    continue
                source_blocks.append(f"Source {i}: {item.url}\n{content[:12000]}")
            if not source_blocks:
                logger.info("Skipping group '%s' — no substantive content", group.group_title[:60])
                continue
            body_block = "\n\n".join(source_blocks)

        role_tag = "[LEAD]" if group.reason.startswith("[LEAD]") else "[SUPPORTING]"
        news_items.append(
            f"### {role_tag} [{group.subcategory}] {group.group_title}\n\n"
            f"{body_block}"
        )

    # Build separate CP block — not mixed into individual news items
    # Option B: insights with quotes get blockquotes; insights with only key_point
    # get a paragraph (no blockquote). Never emit placeholder literals.
    #
    # Defensive cleanup: insights loaded from older checkpoints may still contain
    # quotes wrapped in surrounding quote marks and/or scheme-less URLs. We clean
    # at point-of-use so both new summaries AND legacy checkpoint data are safe.
    import re as _re
    _quote_marks = '"\u201C\u201D\u2018\u2019\''
    _url_pat = _re.compile(
        r"(?:https?://|\b(?:github|arxiv|twitter|x|youtu|youtube|medium|reddit|huggingface|paperswithcode|openai|anthropic|deepmind)\.(?:com|org|be)/)",
        _re.IGNORECASE,
    )

    def _sanitize_quote(q: str) -> str | None:
        """Strip surrounding quote marks; reject if quote contains a URL."""
        if not isinstance(q, str):
            return None
        s = q.strip()
        for _ in range(3):
            if len(s) >= 2 and s[0] in _quote_marks and s[-1] in _quote_marks:
                s = s[1:-1].strip()
            else:
                break
        if len(s) < 10 or _url_pat.search(s):
            return None
        return s

    cp_entries = []
    for group in classified:
        insight = community_summary_map.get(group.primary_url)
        if not insight or not (insight.quotes or insight.key_point):
            continue
        # Sanitize quotes defensively (handles both fresh and checkpoint-loaded data)
        clean_quotes = [s for q in (insight.quotes or []) if (s := _sanitize_quote(q))]
        clean_quotes_ko = [s for q in (insight.quotes_ko or []) if (s := _sanitize_quote(q))]
        # Align lengths: quotes_ko should match quotes count (Writer expects 1:1 mapping)
        clean_quotes_ko = clean_quotes_ko[:len(clean_quotes)]
        has_quotes = bool(clean_quotes)
        parts = [f"Topic: {group.group_title}"]
        parts.append(f"Platform: {insight.source_label}")
        parts.append(f"Sentiment: {insight.sentiment}")
        if has_quotes:
            parts.append(f"HasQuotes: yes — emit {len(clean_quotes)} blockquote(s) below")
            for i, q in enumerate(clean_quotes, start=1):
                parts.append(f'English quote {i}: "{q}"')
            for i, q in enumerate(clean_quotes_ko, start=1):
                parts.append(f'Korean quote {i} (translation of English quote {i}): "{q}"')
        else:
            parts.append("HasQuotes: no — DO NOT emit any blockquote for this topic, write key point as a regular paragraph only")
        if insight.key_point:
            parts.append(f"Key Discussion: {insight.key_point}")
        cp_entries.append("\n".join(parts))

    user_prompt = "\n\n---\n\n".join(news_items)
    if cp_entries:
        user_prompt += (
            "\n\n===\n\nCommunity Pulse Data:\n"
            "Each topic below has a HasQuotes flag. If HasQuotes=yes, emit blockquotes "
            "using 'English quote N' values in en section and matching 'Korean quote N' "
            "values in ko section. If HasQuotes=no, write only a short paragraph based on "
            "Sentiment + Key Discussion — never emit an empty blockquote and never write "
            "the literal text '[EN quote]' or '[KO quote]' in the output.\n\n"
            + "\n\n".join(cp_entries)
        )

    # Generate personas
    client = get_openai_client()
    model = settings.openai_model_main
    personas: dict[str, PersonaOutput] = {}
    digest_headline = ""           # expert headline (becomes news_posts.title for EN)
    digest_headline_ko = ""        # expert headline_ko (becomes news_posts.title for KO)
    digest_excerpt = ""            # expert excerpt
    digest_excerpt_ko = ""         # expert excerpt_ko
    digest_headline_learner = ""           # learner headline (saved to guide_items.title_learner)
    digest_headline_learner_ko = ""        # learner headline_ko
    digest_excerpt_learner = ""            # learner excerpt
    digest_excerpt_learner_ko = ""         # learner excerpt_ko
    persona_sources: dict[str, list[dict]] = {}  # {"expert": [...], "learner": [...]}
    digest_tags: list[str] = []
    digest_focus_items: list[str] = []
    digest_focus_items_ko: list[str] = []
    persona_quizzes: dict[str, dict] = {}  # {"expert": {"en": {...}, "ko": {...}}, "learner": {...}}
    persona_prompts: dict[str, str] = {}

    MAX_DIGEST_RETRIES = 2  # 2 retries = 3 total attempts

    for persona_name in ("expert", "learner"):
        t_p = time.monotonic()
        system_prompt = get_digest_prompt(digest_type, persona_name, handbook_slugs)
        persona_prompts[persona_name] = system_prompt

        for attempt in range(MAX_DIGEST_RETRIES + 1):
            try:
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        **compat_create_kwargs(
                            model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            response_format={"type": "json_object"},
                            temperature=0.4,
                            max_tokens=24000,
                        )
                    ),
                    timeout=240,  # 4 minutes max per digest call
                )
                data = parse_ai_json(
                    response.choices[0].message.content,
                    f"Digest-{digest_type}-{persona_name}",
                )
                persona_output = PersonaOutput(
                    en=_clean_writer_output(data.get("en", "")),
                    ko=_clean_writer_output(data.get("ko", "")),
                )

                # Capture metadata from first persona (expert)
                def _has_ko(s: str) -> bool:
                    return any('\uAC00' <= c <= '\uD7AF' for c in s)
                # Capture metadata: expert call fills the canonical fields (used in DB title/excerpt),
                # learner call fills the persona-specific fields (saved to guide_items for learner display).
                if persona_name == "expert":
                    if not digest_headline and data.get("headline"):
                        h = data["headline"]
                        if _has_ko(h):
                            logger.warning("headline contains Korean, swapping to headline_ko")
                            if not digest_headline_ko:
                                digest_headline_ko = h
                        else:
                            digest_headline = h
                    if not digest_headline_ko and data.get("headline_ko"):
                        digest_headline_ko = data["headline_ko"]
                    if not digest_excerpt and data.get("excerpt"):
                        digest_excerpt = data["excerpt"]
                    if not digest_excerpt_ko and data.get("excerpt_ko"):
                        digest_excerpt_ko = data["excerpt_ko"]
                elif persona_name == "learner":
                    if not digest_headline_learner and data.get("headline"):
                        h = data["headline"]
                        if not _has_ko(h):
                            digest_headline_learner = h
                    if not digest_headline_learner_ko and data.get("headline_ko"):
                        digest_headline_learner_ko = data["headline_ko"]
                    if not digest_excerpt_learner and data.get("excerpt"):
                        digest_excerpt_learner = data["excerpt"]
                    if not digest_excerpt_learner_ko and data.get("excerpt_ko"):
                        digest_excerpt_learner_ko = data["excerpt_ko"]
                if not digest_tags and data.get("tags"):
                    digest_tags = data["tags"]
                if not digest_focus_items and data.get("focus_items"):
                    digest_focus_items = data["focus_items"]
                if not digest_focus_items_ko and data.get("focus_items_ko"):
                    digest_focus_items_ko = data["focus_items_ko"]
                if data.get("sources") and persona_name not in persona_sources:
                    persona_sources[persona_name] = data["sources"]
                # Extract quiz data per persona
                quiz_en = data.get("quiz_en")
                quiz_ko = data.get("quiz_ko")
                if quiz_en or quiz_ko:
                    persona_quizzes[persona_name] = {}
                    if isinstance(quiz_en, dict) and quiz_en.get("question"):
                        persona_quizzes[persona_name]["en"] = quiz_en
                    if isinstance(quiz_ko, dict) and quiz_ko.get("question"):
                        persona_quizzes[persona_name]["ko"] = quiz_ko
                usage = extract_usage_metrics(response, model)
                cumulative_usage = merge_usage_metrics(cumulative_usage, usage)

                # Recover missing locale: re-generate missing side
                ko_recovered = False
                en_recovered = False

                # EN exists but KO empty → recover KO
                if persona_output.en.strip() and not persona_output.ko.strip():
                    logger.warning(
                        "Digest %s %s: EN ok (%d chars) but KO empty — re-generating KO only",
                        digest_type, persona_name, len(persona_output.en),
                    )
                    try:
                        ko_system = (
                            f"{system_prompt}\n\n"
                            "IMPORTANT: Generate ONLY the Korean (ko) content. "
                            "The English version already exists. Return JSON: {{\"ko\": \"...\"}}"
                        )
                        ko_resp = await asyncio.wait_for(
                            client.chat.completions.create(
                                **compat_create_kwargs(
                                    model,
                                    messages=[
                                        {"role": "system", "content": ko_system},
                                        {"role": "user", "content": user_prompt},
                                    ],
                                    response_format={"type": "json_object"},
                                    temperature=0.4,
                                    max_tokens=8000,
                                )
                            ),
                            timeout=120,  # 2 minutes for recovery
                        )
                        ko_data = parse_ai_json(
                            ko_resp.choices[0].message.content,
                            f"Digest-{digest_type}-{persona_name}-ko-recovery",
                        )
                        ko_usage = extract_usage_metrics(ko_resp, model)
                        cumulative_usage = merge_usage_metrics(cumulative_usage, ko_usage)
                        recovered_ko = ko_data.get("ko", "")
                        if recovered_ko.strip():
                            persona_output = PersonaOutput(en=persona_output.en, ko=recovered_ko)
                            ko_recovered = True
                            logger.info(
                                "KO recovery succeeded for %s %s: %d chars",
                                digest_type, persona_name, len(recovered_ko),
                            )
                    except Exception as ko_err:
                        logger.warning("KO recovery failed for %s %s: %s", digest_type, persona_name, ko_err)

                # KO exists but EN empty → recover EN
                if persona_output.ko.strip() and not persona_output.en.strip():
                    logger.warning(
                        "Digest %s %s: KO ok (%d chars) but EN empty — re-generating EN only",
                        digest_type, persona_name, len(persona_output.ko),
                    )
                    try:
                        en_system = (
                            f"{system_prompt}\n\n"
                            "IMPORTANT: Generate ONLY the English (en) content. "
                            "The Korean version already exists. Return JSON: {{\"en\": \"...\"}}"
                        )
                        en_resp = await asyncio.wait_for(
                            client.chat.completions.create(
                                **compat_create_kwargs(
                                    model,
                                    messages=[
                                        {"role": "system", "content": en_system},
                                        {"role": "user", "content": user_prompt},
                                    ],
                                    response_format={"type": "json_object"},
                                    temperature=0.4,
                                    max_tokens=8000,
                                )
                            ),
                            timeout=120,
                        )
                        en_data = parse_ai_json(
                            en_resp.choices[0].message.content,
                            f"Digest-{digest_type}-{persona_name}-en-recovery",
                        )
                        en_usage = extract_usage_metrics(en_resp, model)
                        cumulative_usage = merge_usage_metrics(cumulative_usage, en_usage)
                        recovered_en = en_data.get("en", "")
                        if recovered_en.strip():
                            persona_output = PersonaOutput(en=recovered_en, ko=persona_output.ko)
                            en_recovered = True
                            logger.info(
                                "EN recovery succeeded for %s %s: %d chars",
                                digest_type, persona_name, len(recovered_en),
                            )
                    except Exception as en_err:
                        logger.warning("EN recovery failed for %s %s: %s", digest_type, persona_name, en_err)

                personas[persona_name] = persona_output

                await _log_stage(
                    supabase, run_id,
                    f"digest:{digest_type}:{persona_name}", "success", t_p,
                    output_summary=f"en={len(persona_output.en)}chars, ko={len(persona_output.ko)}chars",
                    usage=usage,
                    post_type=digest_type,
                    attempt=attempt + 1,
                    debug_meta={
                        "attempt": attempt + 1, "attempts": attempt + 1,
                        "ko_recovered": ko_recovered, "en_recovered": en_recovered,
                        "en_length": len(persona_output.en),
                        "ko_length": len(persona_output.ko),
                        "en_preview": _trim(persona_output.en, 500),
                        "ko_preview": _trim(persona_output.ko, 500),
                        "news_count": len(classified),
                    },
                )
                break  # success — no more retries

            except Exception as e:
                logger.warning(
                    "Digest %s %s attempt %d failed: %s",
                    digest_type, persona_name, attempt + 1, e,
                )
                if attempt == MAX_DIGEST_RETRIES:
                    error_msg = f"{digest_type} {persona_name} digest failed after {attempt + 1} attempts: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    await _log_stage(
                        supabase, run_id,
                        f"digest:{digest_type}:{persona_name}", "failed", t_p,
                        error_message=error_msg, post_type=digest_type,
                        attempt=attempt + 1,
                        debug_meta={"attempt": attempt + 1},
                    )

    # Validate: all 3 personas must exist AND have non-empty content
    incomplete = []
    for pname in ("expert", "learner"):
        p = personas.get(pname)
        if not p:
            incomplete.append(f"{pname} (missing)")
        elif not p.en.strip() or not p.ko.strip():
            incomplete.append(f"{pname} (empty content: en={len(p.en)}chars, ko={len(p.ko)}chars)")
    if incomplete:
        error_msg = f"{digest_type} digest incomplete — {', '.join(incomplete)}"
        logger.error(error_msg)
        errors.append(error_msg)
        return 0, errors, cumulative_usage

    # Lazy import to break circular dependency (pipeline_quality ↔ pipeline_digest)
    from services.pipeline_quality import _check_digest_quality, _find_digest_blockers

    blockers = _find_digest_blockers(personas, classified=classified)
    recoverable_en_personas = sorted({
        blocker.split(":", 1)[0].split()[0]
        for blocker in blockers
        if ": Hangul in EN `###` heading " in blocker
    })
    if recoverable_en_personas:
        for persona_name in recoverable_en_personas:
            system_prompt = persona_prompts.get(persona_name) or get_digest_prompt(
                digest_type, persona_name, handbook_slugs,
            )
            try:
                en_system = (
                    f"{system_prompt}\n\n"
                    "IMPORTANT: Generate ONLY the English (en) content. "
                    "The previous English output leaked Korean in one or more `###` headings. "
                    "Regenerate the English content so every `###` heading and body line is fully English. "
                    "Do not include Korean text in the English output. Return JSON: {{\"en\": \"...\"}}"
                )
                en_resp = await asyncio.wait_for(
                    client.chat.completions.create(
                        **compat_create_kwargs(
                            model,
                            messages=[
                                {"role": "system", "content": en_system},
                                {"role": "user", "content": user_prompt},
                            ],
                            response_format={"type": "json_object"},
                            temperature=0.4,
                            max_tokens=8000,
                        )
                    ),
                    timeout=120,
                )
                en_data = parse_ai_json(
                    en_resp.choices[0].message.content,
                    f"Digest-{digest_type}-{persona_name}-en-heading-recovery",
                )
                en_usage = extract_usage_metrics(en_resp, model)
                cumulative_usage = merge_usage_metrics(cumulative_usage, en_usage)
                recovered_en = _clean_writer_output(en_data.get("en", ""))
                if recovered_en.strip():
                    personas[persona_name] = PersonaOutput(
                        en=recovered_en,
                        ko=personas[persona_name].ko,
                    )
                    await _log_stage(
                        supabase,
                        run_id,
                        f"recover:{digest_type}:{persona_name}:en",
                        "success",
                        time.monotonic(),
                        output_summary=f"Recovered EN after locale-heading validation failure ({len(recovered_en)} chars)",
                        usage=en_usage,
                        post_type=digest_type,
                    )
                    logger.info(
                        "EN heading recovery succeeded for %s %s: %d chars",
                        digest_type, persona_name, len(recovered_en),
                    )
            except Exception as en_err:
                logger.warning(
                    "EN heading recovery failed for %s %s: %s",
                    digest_type, persona_name, en_err,
                )
        blockers = _find_digest_blockers(personas, classified=classified)

    if blockers:
        error_msg = f"{digest_type} digest structural validation failed — {'; '.join(blockers)}"
        logger.error(error_msg)
        errors.append(error_msg)
        await _log_stage(
            supabase,
            run_id,
            f"validate:{digest_type}",
            "failed",
            time.monotonic(),
            error_message=error_msg,
            post_type=digest_type,
            debug_meta={"blockers": blockers},
        )
        return 0, errors, cumulative_usage

    frontload_payload = {
        "headline": digest_headline,
        "headline_ko": digest_headline_ko,
        "excerpt": digest_excerpt,
        "excerpt_ko": digest_excerpt_ko,
        "focus_items": digest_focus_items,
        "focus_items_ko": digest_focus_items_ko,
    }

    # Quality check — score the generated digest
    quality_result = await _check_digest_quality(
        personas, digest_type, classified, community_summary_map,
        supabase, run_id, cumulative_usage,
        frontload=frontload_payload,
    )
    if isinstance(quality_result, dict):
        quality_score = int(quality_result.get("score", quality_result.get("quality_score", 0)) or 0)
        quality_meta = quality_result
    else:
        quality_score = int(quality_result or 0)
        quality_meta = {
            "score": quality_score,
            "quality_score": quality_score,
            "quality_version": "v1",
        }

    # Save EN + KO rows
    missing = [p for p in ("expert", "learner") if p not in personas]
    if missing:
        logger.warning("Missing personas for %s digest: %s", digest_type, missing)

    t_save = time.monotonic()
    translation_group_id = str(uuid.uuid4())
    slug_base = f"{batch_id}-{digest_type}-digest"

    fallback_source_urls = [url for group in classified for url in group.urls]
    merged_persona_sources = (
        (persona_sources.get("expert") or []) +
        (persona_sources.get("learner") or [])
    )
    digest_meta = {
        "digest_type": digest_type,
        "news_items": [
            {"title": group.group_title, "url": group.primary_url, "subcategory": group.subcategory}
            for group in classified
        ],
    }

    fallback_title = classified[0].group_title if classified else ""
    type_label = "Research" if digest_type == "research" else "Business"

    for locale in ("en", "ko"):
        slug = slug_base if locale == "en" else f"{slug_base}-ko"
        if locale == "ko":
            title = digest_headline_ko or digest_headline or fallback_title
            if title and not any('\uAC00' <= c <= '\uD7AF' for c in title):
                logger.warning("KO title has no Korean characters, prefixing: %s", title[:50])
                title = f"AI {type_label} 데일리 — {title}"
        else:
            title = digest_headline or fallback_title

        # Calculate reading time from expert content (longest persona)
        expert_content = (personas["expert"].en if locale == "en" else personas["expert"].ko) if "expert" in personas else ""
        learner_content = (personas["learner"].en if locale == "en" else personas["learner"].ko) if "learner" in personas else ""

        # Post-process: fix bold markdown with parenthetical abbreviations
        # **Rejection Fine-Tuning(RFT)** → **Rejection Fine-Tuning** (RFT)
        expert_content = re.sub(r'\*\*([^*]+?)\(([^)]+)\)\*\*', r'**\1** (\2)', expert_content)
        learner_content = re.sub(r'\*\*([^*]+?)\(([^)]+)\)\*\*', r'**\1** (\2)', learner_content)

        # Post-process: remove [LEAD]/[SUPPORTING] tags leaked into output
        # These are input-only signals that LLM sometimes copies into headings
        for tag in ['[LEAD]', '[SUPPORTING]', '([LEAD])', '([SUPPORTING])']:
            expert_content = expert_content.replace(tag, '')
            learner_content = learner_content.replace(tag, '')

        # Post-process: renumber citations sequentially by URL appearance order
        # LLM may reset [1] per section — this forces global sequential numbering.
        # Also strip hallucinated URLs (citations pointing to URLs not in source set).
        allowed_urls: set[str] = set(raw_content_map.keys())
        source_meta_by_url: dict[str, dict[str, str]] = {}
        for url, sources in (enriched_map or {}).items():
            allowed_urls.add(url)
            for s in sources:
                if isinstance(s, dict) and s.get("url"):
                    allowed_urls.add(s["url"])
                    source_meta_by_url[s["url"]] = {
                        "source_kind": s.get("source_kind", ""),
                        "source_confidence": s.get("source_confidence", ""),
                        "source_tier": s.get("source_tier", ""),
                    }
        expert_content, expert_source_cards = _renumber_citations(
            expert_content,
            allowed_urls,
            source_meta_by_url,
        )
        learner_content, learner_source_cards = _renumber_citations(
            learner_content,
            allowed_urls,
            source_meta_by_url,
        )
        combined_source_cards = _dedup_source_cards(
            (expert_source_cards or []) + (learner_source_cards or [])
        )
        if not combined_source_cards and fallback_source_urls:
            combined_source_cards = [
                {
                    "id": idx + 1,
                    "url": url,
                    "title": "",
                    "source_kind": source_meta_by_url.get(url, {}).get("source_kind", ""),
                    "source_confidence": source_meta_by_url.get(url, {}).get("source_confidence", ""),
                    "source_tier": source_meta_by_url.get(url, {}).get("source_tier", ""),
                }
                for idx, url in enumerate(dict.fromkeys(fallback_source_urls))
            ]


        text = expert_content or learner_content or ""
        if locale == "ko":
            # Korean: count characters (excluding spaces/punctuation), ~500 chars/min
            char_count = len([c for c in text if c.strip() and c not in '.,!?;:()[]{}"\'-—·…#*_~`|/>'])
            reading_time = max(1, round(char_count / 500))
        else:
            # English: count words, ~200 words/min
            reading_time = max(1, round(len(text.split()) / 200))

        # Select locale-appropriate excerpt and focus_items
        excerpt = (digest_excerpt if locale == "en" else digest_excerpt_ko) or digest_excerpt or ""
        focus_items = (digest_focus_items if locale == "en" else digest_focus_items_ko) or digest_focus_items or []

        # Always save as draft — promote cron at KST 09:00 decides publish
        # auto_publish param marks whether this draft is eligible for promotion
        row: dict[str, Any] = {
            "title": title,
            "slug": slug,
            "locale": locale,
            "category": "ai-news",
            "post_type": digest_type,
            "status": "draft",
        }
        # Only include content fields when non-empty to avoid overwriting
        # existing data with null on re-runs (upsert replaces entire row)
        if expert_content:
            row["content_expert"] = expert_content
        if learner_content:
            row["content_learner"] = learner_content
        row.update({
            "excerpt": excerpt or None,
            "tags": digest_tags or [],
            "focus_items": focus_items or [],
            "reading_time_min": reading_time,
            "source_urls": [card["url"] for card in combined_source_cards],
            "source_cards": _fill_source_titles(
                combined_source_cards,
                merged_persona_sources,
            ),
            "fact_pack": {
                **digest_meta,
                "quality_score": quality_score,
                "quality_version": quality_meta.get("quality_version", "v1"),
                "quality_breakdown": quality_meta.get("quality_breakdown", {}),
                "quality_issues": quality_meta.get("quality_issues", []),
                "quality_caps_applied": quality_meta.get("quality_caps_applied", []),
                "structural_penalty": quality_meta.get("structural_penalty", 0),
                "structural_warnings": quality_meta.get("structural_warnings", []),
                "auto_publish_eligible": auto_publish,
            },
            "quality_score": quality_score,
            "pipeline_batch_id": batch_id,
            "published_at": f"{batch_id}T00:00:00Z",
            "pipeline_model": settings.openai_model_main,
            "translation_group_id": translation_group_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

        # Build guide_items with persona-specific quizzes and code-extracted sources
        import random as _random
        guide_items: dict[str, Any] = {}
        for pname in ("expert", "learner"):
            quiz = persona_quizzes.get(pname, {}).get("en" if locale == "en" else "ko")
            if quiz and isinstance(quiz, dict) and quiz.get("options") and quiz.get("answer"):
                # Shuffle quiz options so answer isn't always A/B
                options = list(quiz["options"])
                answer = quiz["answer"]
                _random.shuffle(options)
                quiz = {**quiz, "options": options, "answer": answer}
            if quiz:
                guide_items[f"quiz_poll_{pname}"] = quiz
        # Use code-extracted source_cards with LLM-generated titles merged in
        if expert_source_cards:
            guide_items["sources_expert"] = _fill_source_titles(
                expert_source_cards, persona_sources.get("expert") or [],
            )
        if learner_source_cards:
            guide_items["sources_learner"] = _fill_source_titles(
                learner_source_cards, persona_sources.get("learner") or [],
            )
        # Persona-specific title/excerpt for learner (B2 — used in list cards, SNS preview, search)
        learner_title = digest_headline_learner_ko if locale == "ko" else digest_headline_learner
        learner_excerpt = digest_excerpt_learner_ko if locale == "ko" else digest_excerpt_learner
        if learner_title:
            guide_items["title_learner"] = learner_title
        if learner_excerpt:
            guide_items["excerpt_learner"] = learner_excerpt
        if guide_items:
            row["guide_items"] = guide_items

        try:
            supabase.table("news_posts").upsert(row, on_conflict="slug").execute()
            posts_created += 1
            logger.info("Saved %s %s digest draft (score=%s, eligible=%s): %s",
                        digest_type, locale, quality_score, auto_publish, slug)
        except Exception as e:
            error_msg = f"Failed to save {digest_type} {locale} digest: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    await _log_stage(
        supabase, run_id, f"save:{digest_type}",
        "success" if posts_created > 0 else "failed", t_save,
        output_summary=f"{posts_created} draft rows saved (score={quality_score}, eligible={auto_publish})",
        post_type=digest_type,
        debug_meta={"slug_base": slug_base, "locales": ["en", "ko"], "auto_publish_eligible": auto_publish},
    )

    return posts_created, errors, cumulative_usage

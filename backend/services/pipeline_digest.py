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

import openai

from core.config import settings
from models.news_pipeline import (
    ClassifiedGroup,
    CommunityInsight,
    PersonaOutput,
)
from services.agents.citation_substitution import (
    CitationSubstitutionError,
    apply_citations,
)
from services.agents.client import (
    compat_create_kwargs,
    extract_usage_metrics,
    get_openai_client,
    merge_usage_metrics,
    parse_ai_json,
    with_flex_retry,
)
from services.agents.prompts_news_pipeline import get_digest_prompt
from services.agents.schemas.news_writer import build_news_writer_json_schema

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
# Community Pulse citation injection
# ---------------------------------------------------------------------------

_CP_HEADERS = ("## Community Pulse", "## 커뮤니티 반응")

# Block header like `**Hacker News** (79↑)` or `**r/OpenAI** (1.2K↑)`.
# Captures the label text and the upvote count (digits only; we normalize K suffixes).
_CP_BLOCK_HEADER_RE = re.compile(
    r"^\s*(?:-\s+)?\*\*(?P<label>[^*\n]+?)\*\*\s*\(\s*(?P<upvotes>[\d,.]+)(?P<kmult>[Kk]?)\s*↑",
)

# Attribution line `> — <label>` (em-dash OR double hyphen).
_CP_ATTR_RE_TMPL = r"^> [—\-]+ {label}\s*$"

# Upvote count inside CommunityInsight.source_label, e.g. "Hacker News 79↑ · 116 comments"
# or "r/OpenAI (500↑)". Captures the digits/K preceding the ↑ arrow.
_INSIGHT_UPVOTE_RE = re.compile(r"(\d[\d,.]*)(K)?↑", re.IGNORECASE)


def _upvotes_to_int(digits: str, kmult: str) -> int:
    """'1,203' + '' → 1203;   '1.2' + 'K' → 1200."""
    try:
        base = float(digits.replace(",", ""))
    except ValueError:
        return -1
    if kmult and kmult.upper() == "K":
        base *= 1000
    return int(round(base))


def _insight_hn_upvotes(source_label: str) -> int:
    """Extract upvote count of the HN thread from an insight's source_label.
    Returns -1 if not found. Used to match body blocks to insights by count."""
    # We look at the FIRST ↑ in the label (HN comes before Reddit per _parse_source_meta).
    if "Hacker News" not in source_label:
        return -1
    m = _INSIGHT_UPVOTE_RE.search(source_label)
    if not m:
        return -1
    return _upvotes_to_int(m.group(1), m.group(2) or "")


def _insight_reddit_upvotes(source_label: str) -> int:
    """Extract upvote count of the Reddit thread from an insight's source_label.
    Returns -1 if not found."""
    # Look for upvote count AFTER "r/xxx" in the label.
    m = re.search(r"r/\S+?\s*\(\s*(\d[\d,.]*)(K)?↑", source_label, re.IGNORECASE)
    if not m:
        return -1
    return _upvotes_to_int(m.group(1), m.group(2) or "")


def _inject_cp_citations(
    content: str,
    community_summary_map: dict[str, "CommunityInsight"],
) -> str:
    """Linkify `> — <Label>` attribution lines in the Community Pulse section
    using thread URLs from each CommunityInsight (hn_url / reddit_url).

    Matching strategy — by upvote count:
      Body block header `**Hacker News** (79↑)` is paired with the insight
      whose source_label contains "79↑" and has hn_url populated. This avoids
      the positional bug (writer can reorder blocks; dict iteration order
      is independent of body order).

    Degrades safely:
      - No CP section → return content unchanged.
      - Insight has no hn_url/reddit_url (old checkpoint) → attribution stays raw.
      - Block upvote count doesn't match any insight → attribution stays raw.
      - Non-CP blockquotes → never touched (only section-scoped).
    """
    if not community_summary_map or not content:
        return content

    # Build per-platform index of (upvote_count, thread_url). First match wins
    # if two insights happen to share an upvote count (rare; HN/Reddit APIs
    # return integers in different ranges).
    hn_index: list[tuple[int, str]] = []       # (upvotes, hn_url)
    reddit_index: list[tuple[str, int, str]] = []  # (subreddit, upvotes, reddit_url)

    for insight in community_summary_map.values():
        src = getattr(insight, "source_label", "") or ""
        hn_url = getattr(insight, "hn_url", None)
        reddit_url = getattr(insight, "reddit_url", None)

        if hn_url:
            upv = _insight_hn_upvotes(src)
            if upv >= 0:
                hn_index.append((upv, hn_url))

        if reddit_url:
            m_sub = re.search(r"r/(\S+?)(?:\s|\(|$)", src)
            upv = _insight_reddit_upvotes(src)
            if m_sub and upv >= 0:
                reddit_index.append((m_sub.group(1).rstrip(")"), upv, reddit_url))

    if not hn_index and not reddit_index:
        return content

    def _lookup_url(label: str, upvotes: int) -> str | None:
        if label == "Hacker News":
            for upv, url in hn_index:
                if upv == upvotes:
                    return url
            return None
        # r/<subreddit>
        m = re.match(r"r/(\S+)", label)
        if m:
            sub = m.group(1)
            for isub, upv, url in reddit_index:
                if isub == sub and upv == upvotes:
                    return url
        return None

    def _process_section(section_body: str) -> str:
        out_lines: list[str] = []
        current_label: str | None = None
        current_url: str | None = None

        for line in section_body.split("\n"):
            hdr = _CP_BLOCK_HEADER_RE.match(line)
            if hdr:
                label = hdr.group("label").strip()
                upvotes = _upvotes_to_int(hdr.group("upvotes"), hdr.group("kmult"))
                url = _lookup_url(label, upvotes) if upvotes >= 0 else None
                if url:
                    current_label = label
                    current_url = url
                else:
                    current_label = None
                    current_url = None
            elif current_label and current_url:
                attr_pat = re.compile(
                    _CP_ATTR_RE_TMPL.format(label=re.escape(current_label))
                )
                if attr_pat.match(line):
                    line = f"> — [{current_label}]({current_url})"
            out_lines.append(line)
        return "\n".join(out_lines)

    result = content
    for header_text in _CP_HEADERS:
        section_re = re.compile(
            rf"^({re.escape(header_text)}\s*\n)(.*?)(?=^## |\Z)",
            re.MULTILINE | re.DOTALL,
        )
        result = section_re.sub(
            lambda m: m.group(1) + _process_section(m.group(2)),
            result,
        )
    return result


# ---------------------------------------------------------------------------
# CP Data input builder (per-topic entry passed to writer prompt)
# ---------------------------------------------------------------------------

_CP_QUOTE_MARKS = '"""''\''
_CP_URL_PAT = re.compile(
    r"(?:https?://|\b(?:github|arxiv|twitter|x|youtu|youtube|medium|reddit|huggingface|paperswithcode|openai|anthropic|deepmind)\.(?:com|org|be)/)",
    re.IGNORECASE,
)


def _sanitize_cp_quote(q: str) -> str | None:
    """Strip surrounding quote marks up to 3 layers; reject quotes containing URLs
    or shorter than 10 chars (likely garbage or link-only comments)."""
    if not isinstance(q, str):
        return None
    s = q.strip()
    for _ in range(3):
        if len(s) >= 2 and s[0] in _CP_QUOTE_MARKS and s[-1] in _CP_QUOTE_MARKS:
            s = s[1:-1].strip()
        else:
            break
    if len(s) < 10 or _CP_URL_PAT.search(s):
        return None
    return s


def _build_cp_data_entry(
    group: "ClassifiedGroup",
    insight: "CommunityInsight | None",
) -> str | None:
    """Build the CP Data block for a single topic (primary_url → insight).

    Returns None when the insight is missing or has neither quotes nor key_point
    (nothing meaningful to render in CP).
    """
    if insight is None:
        return None
    if not (insight.quotes or insight.key_point):
        return None

    clean_quotes = [s for q in (insight.quotes or []) if (s := _sanitize_cp_quote(q))]
    clean_quotes_ko = [s for q in (insight.quotes_ko or []) if (s := _sanitize_cp_quote(q))]
    # Align lengths: quotes_ko should match quotes count (writer expects 1:1 mapping)
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
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# focus_items_ko fallback
# ---------------------------------------------------------------------------

async def _translate_focus_items_ko(
    items_en: list[str],
    *,
    digest_type: str,
) -> tuple[list[str], dict[str, Any]]:
    """Translate 3 EN focus_items to KO via a cheap gpt-5-mini call.

    Defensive fallback for when the daily writer returns `focus_items` but
    omits `focus_items_ko` — the QC then flags a major locale gap even
    though EN was fine. Prompt hardening (REQUIRED marker in the schema)
    should make this rare, but LLM output is sometimes inconsistent.

    Returns ([], {}) on any failure so the pipeline degrades gracefully
    (the QC will then surface the missing KO frontload as it would have).
    """
    if not items_en or len(items_en) != 3:
        return [], {}

    import json as _json
    client = get_openai_client()
    model = settings.openai_model_light

    system_prompt = (
        "Translate the 3 English focus_items bullets to Korean. "
        "Each Korean bullet: 15-40 characters, same order as input, faithful meaning. "
        "Do not add facts, entities, or numbers that are absent from the English. "
        "Return JSON only: {\"focus_items_ko\": [\"...\", \"...\", \"...\"]}."
    )
    user_prompt = _json.dumps({"focus_items": items_en}, ensure_ascii=False)

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
                    max_tokens=400,
                )
            ),
            timeout=30,
        )
        data = parse_ai_json(
            response.choices[0].message.content,
            f"focus_items_ko_fallback-{digest_type}",
        )
        items_ko = data.get("focus_items_ko")
        if (
            isinstance(items_ko, list)
            and len(items_ko) == 3
            and all(isinstance(x, str) and x.strip() for x in items_ko)
        ):
            usage = extract_usage_metrics(response, model)
            logger.info(
                "focus_items_ko fallback succeeded for %s: %d chars avg",
                digest_type,
                sum(len(x) for x in items_ko) // 3,
            )
            return list(items_ko), usage
        logger.warning(
            "focus_items_ko fallback returned invalid shape for %s: %r",
            digest_type, items_ko,
        )
    except Exception as e:
        logger.warning("focus_items_ko fallback failed for %s: %s", digest_type, e)
    return [], {}


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
    cp_entries: list[str] = []
    for group in classified:
        insight = community_summary_map.get(group.primary_url)
        entry = _build_cp_data_entry(group, insight)
        if entry is not None:
            cp_entries.append(entry)

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

    # Build URL allowlist matching pipeline_quality._check_digest_quality (line 588+):
    # every group.items[].url + every enriched_map anchor/related URL. The strict
    # json_schema uses this as an enum, so the API rejects any URL the writer
    # emits that isn't in the allowlist — writer hallucination is blocked at the
    # API layer, not after the fact.
    allowlist_urls: list[str] = []
    for group in classified:
        for item in (group.items or []):
            if getattr(item, "url", None):
                allowlist_urls.append(item.url)
    for anchor_url, enriched_list in (_enriched or {}).items():
        if anchor_url:
            allowlist_urls.append(anchor_url)
        for entry in (enriched_list or []):
            url = entry.get("url") if isinstance(entry, dict) else None
            if url:
                allowlist_urls.append(url)

    if not allowlist_urls:
        logger.error(
            "Cannot build strict writer schema for %s: no URLs in classified+enriched",
            digest_type,
        )
        return 0, [f"{digest_type}: empty URL allowlist"], {}

    writer_schema = build_news_writer_json_schema(allowlist_urls)

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
                async def _writer_call() -> Any:
                    return await asyncio.wait_for(
                        client.chat.completions.create(
                            **compat_create_kwargs(
                                model,
                                messages=[
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": user_prompt},
                                ],
                                response_format={
                                    "type": "json_schema",
                                    "json_schema": writer_schema,
                                },
                                max_tokens=24000,
                                # 2026-04-23 A/B: research expert benefits
                                # clearly (30 vs 17 cites on multi-paper
                                # synthesis); business ~tied. Chose uniform
                                # "high" for simplicity + consistency —
                                # ~$2/month over mixed config.
                                reasoning_effort="high",
                                service_tier="flex",
                                prompt_cache_key=f"digest-{digest_type}-{persona_name}",
                            )
                        ),
                        # Flex: 15-min headroom per OpenAI guidance. Accommodates
                        # high-reasoning writer (typically 3-5 min) plus queue
                        # time on flex tier.
                        timeout=900,
                    )

                response = await with_flex_retry(_writer_call)
                data = parse_ai_json(
                    response.choices[0].message.content,
                    f"Digest-{digest_type}-{persona_name}",
                )
                # Writer emits [CITE_N] placeholders + citations[] sidecar.
                # Strict schema enum guarantees every url is in the allowlist.
                first_call_citations = data.get("citations") or []
                try:
                    body_en = apply_citations(data.get("en", ""), first_call_citations)
                    body_ko = apply_citations(data.get("ko", ""), first_call_citations)
                except CitationSubstitutionError as sub_err:
                    logger.warning(
                        "Citation substitution failed for %s/%s attempt %d: %s",
                        digest_type, persona_name, attempt, sub_err,
                    )
                    if attempt < MAX_DIGEST_RETRIES:
                        continue
                    raise
                persona_output = PersonaOutput(
                    en=_clean_writer_output(body_en),
                    ko=_clean_writer_output(body_ko),
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
                            "IMPORTANT: Generate ONLY the Korean (ko) content using [CITE_N] "
                            "placeholders that match the citations array from the main output. "
                            "The English version already exists. Return JSON: "
                            "{{\"ko\": \"...[CITE_1]...\"}}"
                        )
                        async def _ko_recovery_call() -> Any:
                            return await asyncio.wait_for(
                                client.chat.completions.create(
                                    **compat_create_kwargs(
                                        model,
                                        messages=[
                                            {"role": "system", "content": ko_system},
                                            {"role": "user", "content": user_prompt},
                                        ],
                                        response_format={"type": "json_object"},
                                        max_tokens=8000,
                                        service_tier="flex",
                                        prompt_cache_key=f"digest-{digest_type}-{persona_name}-ko-recovery",
                                    )
                                ),
                                timeout=300,  # flex recovery: 5-min headroom
                            )

                        ko_resp = await with_flex_retry(_ko_recovery_call)
                        ko_data = parse_ai_json(
                            ko_resp.choices[0].message.content,
                            f"Digest-{digest_type}-{persona_name}-ko-recovery",
                        )
                        ko_usage = extract_usage_metrics(ko_resp, model)
                        cumulative_usage = merge_usage_metrics(cumulative_usage, ko_usage)
                        recovered_ko_raw = ko_data.get("ko", "")
                        if recovered_ko_raw.strip():
                            try:
                                recovered_ko = apply_citations(recovered_ko_raw, first_call_citations)
                            except CitationSubstitutionError as sub_err:
                                logger.warning(
                                    "KO recovery substitution failed for %s %s: %s",
                                    digest_type, persona_name, sub_err,
                                )
                                recovered_ko = ""
                        else:
                            recovered_ko = ""
                        if recovered_ko:
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
                            "IMPORTANT: Generate ONLY the English (en) content using [CITE_N] "
                            "placeholders that match the citations array from the main output. "
                            "The Korean version already exists. Return JSON: "
                            "{{\"en\": \"...[CITE_1]...\"}}"
                        )
                        async def _en_recovery_call() -> Any:
                            return await asyncio.wait_for(
                                client.chat.completions.create(
                                    **compat_create_kwargs(
                                        model,
                                        messages=[
                                            {"role": "system", "content": en_system},
                                            {"role": "user", "content": user_prompt},
                                        ],
                                        response_format={"type": "json_object"},
                                        max_tokens=8000,
                                        service_tier="flex",
                                        prompt_cache_key=f"digest-{digest_type}-{persona_name}-en-recovery",
                                    )
                                ),
                                timeout=300,  # flex recovery: 5-min headroom
                            )

                        en_resp = await with_flex_retry(_en_recovery_call)
                        en_data = parse_ai_json(
                            en_resp.choices[0].message.content,
                            f"Digest-{digest_type}-{persona_name}-en-recovery",
                        )
                        en_usage = extract_usage_metrics(en_resp, model)
                        cumulative_usage = merge_usage_metrics(cumulative_usage, en_usage)
                        recovered_en_raw = en_data.get("en", "")
                        if recovered_en_raw.strip():
                            try:
                                recovered_en = apply_citations(recovered_en_raw, first_call_citations)
                            except CitationSubstitutionError as sub_err:
                                logger.warning(
                                    "EN recovery substitution failed for %s %s: %s",
                                    digest_type, persona_name, sub_err,
                                )
                                recovered_en = ""
                        else:
                            recovered_en = ""
                        if recovered_en:
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

            except openai.BadRequestError as schema_err:
                # Strict json_schema validation failed (after OpenAI's own 2
                # internal retries). Log details and retry the whole call —
                # the next attempt might produce a compliant response.
                logger.warning(
                    "Writer strict-schema rejection on %s %s attempt %d: %s",
                    digest_type, persona_name, attempt + 1, schema_err,
                )
                if attempt == MAX_DIGEST_RETRIES:
                    error_msg = (
                        f"{digest_type} {persona_name} digest failed after "
                        f"{attempt + 1} attempts (schema): {schema_err}"
                    )
                    logger.error(error_msg)
                    errors.append(error_msg)
                    await _log_stage(
                        supabase, run_id,
                        f"digest:{digest_type}:{persona_name}", "failed", t_p,
                        error_message=error_msg, post_type=digest_type,
                        attempt=attempt + 1,
                        debug_meta={"attempt": attempt + 1, "reason": "strict_schema_reject"},
                    )

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
                async def _en_heading_recovery_call() -> Any:
                    return await asyncio.wait_for(
                        client.chat.completions.create(
                            **compat_create_kwargs(
                                model,
                                messages=[
                                    {"role": "system", "content": en_system},
                                    {"role": "user", "content": user_prompt},
                                ],
                                response_format={"type": "json_object"},
                                max_tokens=8000,
                                service_tier="flex",
                                prompt_cache_key=f"digest-{digest_type}-{persona_name}-en-heading-recovery",
                            )
                        ),
                        timeout=300,  # flex recovery: 5-min headroom
                    )

                en_resp = await with_flex_retry(_en_heading_recovery_call)
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

    # Defensive fallback: writer sometimes returns focus_items without focus_items_ko
    # despite the REQUIRED marker in the prompt. Catch it here with a cheap mini-model
    # translation so QC sees a symmetric bilingual frontload.
    if digest_focus_items and not digest_focus_items_ko:
        translated, translate_usage = await _translate_focus_items_ko(
            digest_focus_items, digest_type=digest_type,
        )
        if translated:
            digest_focus_items_ko = translated
            cumulative_usage = merge_usage_metrics(cumulative_usage, translate_usage)

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
        enriched_map=enriched_map,
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

    # Phase 2 — URL strict allowlist: force draft if LLM cited URLs outside fact_pack.
    # _check_digest_quality sets these flags on quality_meta; honour them here so
    # caller-provided auto_publish=True cannot override a validation failure.
    if quality_meta.get("url_validation_failed"):
        logger.warning(
            "Forcing auto_publish=False for %s digest: URL validation failed",
            digest_type,
        )
        auto_publish = False

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
    _group_by_url = {group.primary_url: group for group in classified}

    def _news_items_from_source_cards(
        source_cards: list[dict],
    ) -> list[dict]:
        """Build fact_pack.news_items from citations actually present in body.

        `source_cards` (produced by _renumber_citations) is the set of URLs
        that survived live-check + allowlist. Include every one so readers
        and admin tools see the full cited set — primary + enriched both.
        Falls back to primary_urls if the body had no citations at all.
        """
        if source_cards:
            items: list[dict] = []
            for card in source_cards:
                url = card.get("url") if isinstance(card, dict) else None
                if not url:
                    continue
                group = _group_by_url.get(url)
                if group is not None:
                    items.append({
                        "title": group.group_title,
                        "url": url,
                        "subcategory": group.subcategory,
                    })
                else:
                    items.append({
                        "title": "",
                        "url": url,
                        "subcategory": "enriched",
                    })
            return items
        return [
            {"title": g.group_title, "url": g.primary_url, "subcategory": g.subcategory}
            for g in classified
        ]

    digest_meta = {
        "digest_type": digest_type,
        # Placeholder — overridden per-locale below using combined_source_cards.
        "news_items": _news_items_from_source_cards([]),
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
        # Also strip URLs not in the writer's source set (defense-in-depth —
        # the writer's strict json_schema already enums citations[].url to this
        # same set, so in the happy path nothing gets stripped here).
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

        # Historical note (2026-04-23 removed): previously we HEAD-checked each
        # URL here via _validate_urls_live and dropped dead ones from the
        # allowlist. This was defense against writer hallucinating URLs — but
        # the writer's strict json_schema + citations[].url enum (added today)
        # already rules that out at the API boundary. In practice the HEAD
        # check produced high false-positive rates (70-85% of URLs flagged as
        # timeout/connect on arxiv, github, etc.) and destroyed legitimate
        # citations. If a site genuinely goes 404 between write and read, the
        # reader clicks through and sees 404 — minor UX loss, far outweighed
        # by the citation density we gain back.

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

        # Linkify CP blockquote attributions using community_summary_map URLs.
        # Runs AFTER _renumber_citations so the regex doesn't interact with
        # body [N](URL) citations (those are in a different format).
        expert_content = _inject_cp_citations(expert_content, community_summary_map)
        learner_content = _inject_cp_citations(learner_content, community_summary_map)
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
                "news_items": _news_items_from_source_cards(combined_source_cards),
                "quality_score": quality_score,
                "quality_version": quality_meta.get("quality_version", "v1"),
                "quality_breakdown": quality_meta.get("quality_breakdown", {}),
                # Per-QC-call v11 sub-score breakdowns with evidence — surfaced in admin drill-down (NQ-34).
                # ~1-2KB each for evidence strings; JSONB storage is cheap and the explainability
                # trail is critical for auto-publish decisions.
                "expert_breakdown": quality_meta.get("expert_breakdown", {}),
                "learner_breakdown": quality_meta.get("learner_breakdown", {}),
                "frontload_breakdown": quality_meta.get("frontload_breakdown", {}),
                "quality_issues": quality_meta.get("quality_issues", []),
                "quality_caps_applied": quality_meta.get("quality_caps_applied", []),
                "structural_penalty": quality_meta.get("structural_penalty", 0),
                "structural_warnings": quality_meta.get("structural_warnings", []),
                "auto_publish_eligible": auto_publish,
                # Phase 2 — surface URL validation outcome to DB for admin visibility
                "url_validation_failed": bool(quality_meta.get("url_validation_failed", False)),
                "url_validation_failures": quality_meta.get("url_validation_failures", []),
            },
            "quality_score": quality_score,
            "pipeline_batch_id": batch_id,
            "published_at": f"{batch_id}T00:00:00Z",
            "pipeline_model": settings.openai_model_main,
            "translation_group_id": translation_group_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

        # Build guide_items with persona-specific quizzes and code-extracted sources.
        # Quiz validation (_validate_and_shuffle_quiz_item): requires answer to
        # be verbatim text of one of options — drops letter-form answers ("A")
        # that would silently break after shuffle.
        from services.pipeline import _validate_and_shuffle_quiz_item
        guide_items: dict[str, Any] = {}
        for pname in ("expert", "learner"):
            raw_quiz = persona_quizzes.get(pname, {}).get("en" if locale == "en" else "ko")
            quiz = _validate_and_shuffle_quiz_item(
                raw_quiz, label=f"Daily quiz {digest_type}/{pname}/{locale}"
            )
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
        row["title_learner"] = learner_title if learner_title else None
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

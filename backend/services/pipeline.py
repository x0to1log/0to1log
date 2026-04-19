"""AI News Pipeline v3 orchestrator."""
import asyncio
import logging
import random
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from core.config import settings, today_kst
from core.database import get_supabase
from models.news_pipeline import (
    ClassificationResult,
    ClassifiedGroup,
    CommunityInsight,
    PersonaOutput,
    PipelineResult,
)
from services.agents.advisor import (
    extract_terms_from_content,
    gate_candidate_terms,
    generate_term_content,
)
from services.agents.client import compat_create_kwargs, extract_usage_metrics, get_openai_client, merge_usage_metrics, parse_ai_json
from services.agents.ranking import classify_candidates, merge_classified, rank_classified, summarize_community
from services.handbook_validators import validate_term_scope, validate_korean_name, validate_term_grounding
from services.news_collection import collect_community_reactions, collect_news, enrich_sources

logger = logging.getLogger(__name__)


def _extract_publisher(url: str) -> str:
    """Extract publisher name from URL domain."""
    from urllib.parse import urlparse
    try:
        host = urlparse(url).netloc.lower()
        # Remove www. prefix
        if host.startswith("www."):
            host = host[4:]
        # Remove common TLDs for cleaner display
        parts = host.split(".")
        if len(parts) >= 2:
            return parts[-2].capitalize() if parts[-2] not in ("co", "com") else parts[-3].capitalize() if len(parts) >= 3 else parts[0].capitalize()
        return host.capitalize()
    except Exception:
        return ""


def _fill_source_titles(
    code_cards: list[dict], llm_sources: list[dict],
) -> list[dict]:
    """Merge LLM-generated titles and publisher into code-extracted source_cards."""
    if not code_cards:
        return code_cards
    url_to_title: dict[str, str] = {}
    for src in llm_sources:
        url = src.get("url", "")
        title = src.get("title", "")
        if url and title:
            url_to_title[url] = title
    return [
        {
            **card,
            "title": url_to_title.get(card["url"], card.get("title", "")),
            "publisher": card.get("publisher") or _extract_publisher(card.get("url", "")),
        }
        for card in code_cards
    ]


# Stopwords excluded from entity-overlap dedup. These are generic words that
# would create false positives if counted as "entity" tokens. Includes common
# news verbs, prepositions, and AI-generic terms.
_DEDUP_STOPWORDS = frozenset({
    "the", "and", "for", "with", "from", "into", "this", "that", "their", "more",
    "but", "not", "are", "was", "were", "has", "have", "had", "will", "can", "may",
    "ai", "llm", "gpt", "model", "models", "tool", "tools", "new", "first", "best",
    "now", "soon", "today", "yesterday", "week", "weeks", "year", "years", "day",
    "report", "reports", "news", "study", "research", "test", "tests", "version",
    "release", "releases", "launch", "launches", "launched", "released", "introduces",
    "announces", "announced", "unveils", "unveiled", "shows", "showed", "says",
    "raises", "raised", "billion", "million", "open", "source", "free",
    "company", "companies", "team", "teams", "user", "users", "data",
})


def _extract_entity_tokens(title: str) -> set[str]:
    """Extract proper-noun-ish tokens from a title for dedup matching.

    Heuristic: any word that starts with an uppercase letter, OR contains
    a digit, OR is at least 4 chars and not in stopwords. Lowercased for
    case-insensitive comparison. The goal is to capture entity tokens
    (company names, product names, version numbers) while filtering out
    generic news vocabulary.
    """
    import re as _re
    tokens: set[str] = set()
    # Split on whitespace and common punctuation; preserve hyphenated names
    raw_words = _re.findall(r"[A-Za-z][A-Za-z0-9\-]*|\d+[A-Z]?", title)
    for word in raw_words:
        normalized = word.lower().strip("-")
        if not normalized or len(normalized) < 3:
            continue
        if normalized in _DEDUP_STOPWORDS:
            continue
        # Keep if: started with uppercase (proper noun), or has a digit (version),
        # or is at least 4 chars (substantive word, possibly entity)
        if word[0].isupper() or any(ch.isdigit() for ch in word) or len(normalized) >= 4:
            tokens.add(normalized)
    return tokens


# Action verbs that signal a structurally NEW event about a previously-covered
# entity. If a candidate title contains any of these (case-insensitive substring),
# the entity-overlap dedup is bypassed. Major M&A and corporate actions get through
# even when company names overlap with recent headlines.
_DEDUP_BYPASS_VERBS = (
    "acquires", "acquisition", "buys", "bought", "merger",
    "sues", "lawsuit", "files suit", "filed suit",
    "lays off", "layoff", "fires",
    "files for ipo", "ipo filing",
    "files for bankruptcy", "shuts down", "closes",
    "resigns", "steps down", "fired",
    "raids", "investigates", "fines", "fined",
    "인수", "합병", "고소", "제소", "해고", "사임", "파산",
)


def _filter_recent_duplicates(
    classified: ClassificationResult,
    recent_headlines: list[str],
    overlap_threshold: int = 2,
) -> tuple[ClassificationResult, list[str]]:
    """Drop classified candidates whose entity tokens overlap heavily with
    any recent headline. Code-level safety net for when the LLM ignores the
    prompt-level dedup instruction.

    Bypass: if the candidate title contains a major-action verb from
    _DEDUP_BYPASS_VERBS, it is NOT dropped even when entities overlap, because
    such verbs signal a structurally new event (acquisition, lawsuit, etc.).

    Returns (filtered_result, dropped_titles).
    """
    if not recent_headlines:
        return classified, []

    recent_token_sets = [_extract_entity_tokens(h) for h in recent_headlines]
    dropped: list[str] = []

    def _has_bypass_verb(title: str) -> bool:
        title_lower = title.lower()
        return any(verb in title_lower for verb in _DEDUP_BYPASS_VERBS)

    def _is_dup(candidate_title: str) -> bool:
        if _has_bypass_verb(candidate_title):
            return False  # major structural event — let it through
        cand_tokens = _extract_entity_tokens(candidate_title)
        if len(cand_tokens) < 2:
            return False  # too few tokens to confidently match
        for recent_tokens in recent_token_sets:
            overlap = cand_tokens & recent_tokens
            if len(overlap) >= overlap_threshold:
                return True
        return False

    filtered = ClassificationResult()
    for category in ("research_picks", "business_picks"):
        kept = []
        for c in getattr(classified, category):
            if _is_dup(c.title):
                dropped.append(f"{category[:-6]}: {c.title}")
                logger.info("Dedup drop: %s", c.title[:100])
            else:
                kept.append(c)
        setattr(filtered, category, kept)
    return filtered, dropped


def _renumber_citations(
    content: str,
    allowed_urls: set[str] | None = None,
    source_meta_by_url: dict[str, dict[str, str]] | None = None,
) -> tuple[str, list[dict]]:
    """Renumber all [N](URL) citations sequentially by URL first-appearance order.

    Same URL always gets the same number. Returns (renumbered_content, source_cards).
    source_cards: [{id: 1, url: "...", title: ""}, ...] in order of appearance.

    If allowed_urls is provided, citations pointing to URLs not in the allowlist
    are stripped (LLM hallucination guard) and a warning is logged.
    """
    if not content:
        return content, []

    citation_re = re.compile(r'\[(\d+)\]\(([^)]+)\)')
    url_to_num: dict[str, int] = {}
    source_cards: list[dict] = []
    stripped_urls: list[str] = []

    def _is_allowed(url: str) -> bool:
        if allowed_urls is None:
            return True
        # Match exact, prefix, or suffix (handle trailing slashes, query params)
        url_norm = url.rstrip("/")
        return any(
            url == src or url_norm == src.rstrip("/") or url.startswith(src.rstrip("/"))
            or src.startswith(url_norm)
            for src in allowed_urls
        )

    def _assign(url: str) -> int:
        if url not in url_to_num:
            num = len(url_to_num) + 1
            url_to_num[url] = num
            meta = (source_meta_by_url or {}).get(url, {})
            source_cards.append(
                {
                    "id": num,
                    "url": url,
                    "title": "",
                    "source_kind": meta.get("source_kind", ""),
                    "source_confidence": meta.get("source_confidence", ""),
                    "source_tier": meta.get("source_tier", ""),
                }
            )
        return url_to_num[url]

    def _replace(match: re.Match) -> str:
        url = match.group(2)
        if not _is_allowed(url):
            stripped_urls.append(url)
            return ""  # Strip the citation entirely
        new_num = _assign(url)
        return f"[{new_num}]({url})"

    renumbered = citation_re.sub(_replace, content)
    if stripped_urls:
        logger.warning(
            "Stripped %d hallucinated citation(s): %s",
            len(stripped_urls),
            ", ".join(set(stripped_urls))[:300],
        )
    return renumbered, source_cards



def _dedup_source_cards(sources: list[dict]) -> list[dict]:
    """Deduplicate source cards by URL and re-number IDs from 1."""
    seen: set[str] = set()
    deduped: list[dict] = []
    for s in sources:
        url = s.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append({**s, "id": len(deduped) + 1})
    return deduped


def _validate_and_shuffle_weekly_quiz(quiz_list: Any) -> list[dict]:
    """Validate each weekly quiz item and shuffle its options.

    Keeps up to 3 valid items (drops extras). An item is valid when:
    - It is a dict with non-empty question, 4 string options, and an answer
    - answer is one of options (verbatim match)

    Each valid item's options are shuffled independently. LLMs tend to
    place the correct answer at the first option; shuffling evens out
    the distribution — mirrors the daily quiz shuffle in pipeline_digest.
    """
    cleaned: list[dict] = []
    if not isinstance(quiz_list, list):
        return cleaned
    for q in quiz_list[:3]:
        if not isinstance(q, dict):
            continue
        question = str(q.get("question") or "").strip()
        options_raw = q.get("options")
        answer = str(q.get("answer") or "").strip()
        explanation = str(q.get("explanation") or "").strip()
        if not isinstance(options_raw, list):
            logger.warning("Weekly quiz item dropped: options not a list")
            continue
        options = [str(o).strip() for o in options_raw]
        if not question or len(options) != 4 or answer not in options:
            logger.warning(
                "Weekly quiz item dropped (invalid): q_len=%d options=%d answer_in=%s",
                len(question), len(options), answer in options,
            )
            continue
        shuffled = list(options)
        random.shuffle(shuffled)
        cleaned.append({
            "question": question,
            "options": shuffled,
            "answer": answer,
            "explanation": explanation,
        })
    return cleaned


def _validate_focus_items(items: Any) -> list[str]:
    """Normalize LLM focus_items output to exactly 3 non-empty strings, else [].

    All-or-nothing by design: a partial focus_items list confuses the sidebar
    more than missing them entirely.
    """
    if not isinstance(items, list) or len(items) != 3:
        return []
    cleaned = [str(item).strip() for item in items]
    if any(not c for c in cleaned):
        return []
    return cleaned


def _slugify(text: str) -> str:
    """Generate a URL-safe slug from text."""
    import re
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')[:80]


def _fetch_handbook_slugs(supabase) -> list[str]:
    """Fetch all published handbook term slugs."""
    try:
        result = (
            supabase.table("handbook_terms")
            .select("slug")
            .eq("status", "published")
            .execute()
        )
        return [row["slug"] for row in (result.data or [])]
    except Exception as e:
        logger.warning("Failed to fetch handbook slugs: %s", e)
        return []


def _check_pipeline_health(
    stage: str,
    *,
    classify_picks: tuple[int, int] | None = None,
    merge_groups: list | None = None,
    community_total: int | None = None,
    community_found: int | None = None,
    enrich_map: dict | None = None,
    all_groups: list | None = None,
) -> list[str]:
    """Run stage-specific health checks. Returns list of warning strings."""
    warnings: list[str] = []

    if stage == "classify" and classify_picks:
        r, b = classify_picks
        if r == 0 and b == 0:
            warnings.append("classify: 0 picks for both categories")
        elif r == 0:
            warnings.append("classify: 0 research picks")
        elif b == 0:
            warnings.append("classify: 0 business picks")

    if stage == "merge" and merge_groups is not None:
        for g in merge_groups:
            if len(g.items) >= 8:
                warnings.append(f"merge: group '{g.group_title[:50]}' has {len(g.items)} items (possible over-grouping)")
            if len(g.items) >= 2:
                urls = [i.url for i in g.items]
                if len(set(urls)) < len(urls):
                    warnings.append(f"merge: group '{g.group_title[:50]}' has duplicate URLs")

    if stage == "community" and community_total is not None:
        if community_found == 0 and community_total > 0:
            warnings.append(f"community: 0 reactions from {community_total} queries")

    if stage == "enrich" and enrich_map is not None and all_groups is not None:
        zero_source = [g.group_title[:50] for g in all_groups if not enrich_map.get(g.primary_url)]
        if zero_source:
            warnings.append(f"enrich: {len(zero_source)} groups with 0 sources: {zero_source[:3]}")

    return warnings


def _save_checkpoint(supabase, run_id: str, stage: str, data: dict) -> None:
    """Save pipeline stage output as a checkpoint for rerun support."""
    try:
        supabase.table("pipeline_checkpoints").upsert(
            {"run_id": run_id, "stage": stage, "data": data},
            on_conflict="run_id,stage",
        ).execute()
    except Exception as e:
        logger.warning("Failed to save checkpoint %s: %s", stage, e)


def _load_checkpoint(supabase, run_id: str, stage: str) -> dict | None:
    """Load a checkpoint from a previous run. Returns None if not found."""
    try:
        result = (
            supabase.table("pipeline_checkpoints")
            .select("data")
            .eq("run_id", run_id)
            .eq("stage", stage)
            .single()
            .execute()
        )
        return result.data.get("data") if result.data else None
    except Exception as e:
        logger.warning("Failed to load checkpoint %s for run %s: %s", stage, run_id, e)
        return None


async def _log_stage(
    supabase,
    run_id: str,
    stage: str,
    status: str,
    start_time: float,
    *,
    input_summary: str = "",
    output_summary: str = "",
    error_message: str | None = None,
    usage: dict[str, Any] | None = None,
    post_type: str | None = None,
    locale: str | None = None,
    attempt: int | None = None,
    debug_meta: dict[str, Any] | None = None,
) -> None:
    """Log a pipeline stage to pipeline_logs. Never raises."""
    duration_ms = int((time.monotonic() - start_time) * 1000)
    usage = usage or {}

    # Merge input/output tokens into debug_meta for easy UI access
    meta = dict(debug_meta or {})
    if usage.get("input_tokens"):
        meta["input_tokens"] = usage["input_tokens"]
    if usage.get("output_tokens"):
        meta["output_tokens"] = usage["output_tokens"]

    # Build log row, omitting None values to let DB defaults apply
    # (attempt is NOT NULL DEFAULT 0, debug_meta is NOT NULL DEFAULT '{}')
    log_row: dict[str, Any] = {
        "run_id": run_id,
        "pipeline_type": stage,
        "status": status,
        "duration_ms": duration_ms,
    }
    if input_summary:
        log_row["input_summary"] = input_summary
    if output_summary:
        log_row["output_summary"] = output_summary
    if error_message:
        log_row["error_message"] = error_message
    if usage.get("model_used"):
        log_row["model_used"] = usage["model_used"]
    if usage.get("tokens_used"):
        log_row["tokens_used"] = usage["tokens_used"]
    if usage.get("cost_usd") is not None:
        log_row["cost_usd"] = usage["cost_usd"]
    if post_type:
        log_row["post_type"] = post_type
    if locale:
        log_row["locale"] = locale
    if attempt is not None:
        log_row["attempt"] = attempt
    if meta:
        log_row["debug_meta"] = meta

    try:
        supabase.table("pipeline_logs").insert(log_row).execute()
    except Exception as e:
        logger.warning("Failed to log stage %s: %s", stage, e)


def _trim(text: str | None, max_len: int = 1000) -> str:
    """Trim text to max_len for debug_meta storage."""
    if not text:
        return ""
    return text[:max_len] + ("..." if len(text) > max_len else "")


def check_existing_batch(batch_id: str) -> dict[str, Any] | None:
    """Check if data already exists for a batch_id.

    Returns info dict if data exists, None otherwise.
    """
    supabase = get_supabase()
    if not supabase:
        return None

    run_key = f"news-{batch_id}"
    runs = supabase.table("pipeline_runs").select("id, status, started_at").eq("run_key", run_key).execute()
    posts = supabase.table("news_posts").select("id, status").eq("pipeline_batch_id", batch_id).execute()

    run_data = runs.data or []
    post_data = posts.data or []

    if not run_data and not post_data:
        return None

    published_count = sum(1 for p in post_data if p.get("status") == "published")
    last_run = run_data[0] if run_data else None

    return {
        "run_count": len(run_data),
        "post_count": len(post_data),
        "published_count": published_count,
        "last_status": last_run.get("status") if last_run else None,
        "last_run_at": last_run.get("started_at") if last_run else None,
    }


def cleanup_existing_batch(batch_id: str) -> dict[str, int]:
    """Delete existing pipeline data for a batch_id.

    Raises ValueError if published posts exist.
    Returns cleanup summary.
    """
    supabase = get_supabase()
    if not supabase:
        return {"deleted_runs": 0, "deleted_logs": 0, "deleted_posts": 0}

    run_key = f"news-{batch_id}"

    # Check for published posts first
    published = (
        supabase.table("news_posts")
        .select("id")
        .eq("pipeline_batch_id", batch_id)
        .eq("status", "published")
        .execute()
    )
    if published.data:
        raise ValueError(
            f"{len(published.data)} published posts exist for {batch_id} — cannot overwrite"
        )

    # Get run IDs for log cleanup
    runs = supabase.table("pipeline_runs").select("id").eq("run_key", run_key).execute()
    run_ids = [r["id"] for r in (runs.data or [])]

    # Delete pipeline_logs first (no ON DELETE CASCADE)
    deleted_logs = 0
    for rid in run_ids:
        result = supabase.table("pipeline_logs").delete().eq("run_id", rid).execute()
        deleted_logs += len(result.data or [])

    # Delete pipeline_runs (pipeline_artifacts has ON DELETE CASCADE)
    if run_ids:
        supabase.table("pipeline_runs").delete().eq("run_key", run_key).execute()

    # Delete news_posts
    posts = supabase.table("news_posts").delete().eq("pipeline_batch_id", batch_id).execute()
    deleted_posts = len(posts.data or [])

    logger.info(
        "Cleaned up batch %s: %d runs, %d logs, %d posts",
        batch_id, len(run_ids), deleted_logs, deleted_posts,
    )
    return {"deleted_runs": len(run_ids), "deleted_logs": deleted_logs, "deleted_posts": deleted_posts}



async def _extract_and_create_handbook_terms(
    article_texts: list[str],
    supabase,
    run_id: str,
) -> tuple[int, list[str]]:
    """Extract AI terms from news articles and create handbook drafts.

    Returns (terms_created, errors). Never raises — errors are logged.
    """
    terms_created = 0
    errors: list[str] = []

    combined = "\n\n---\n\n".join(article_texts)
    if not combined.strip():
        return 0, []

    # Step 1: Extract terms per article independently, then merge
    t0 = time.monotonic()
    all_extracted: list[dict] = []
    total_usage: dict = {}
    try:
        results = await asyncio.gather(
            *[extract_terms_from_content(text) for text in article_texts if text.strip()],
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Handbook term extraction failed for one article: %s", result)
                continue
            terms, usage = result
            all_extracted.extend(terms)
            total_usage = merge_usage_metrics(total_usage, usage) if total_usage else usage

        # Deduplicate across articles: keep first occurrence by lowercase term
        seen_terms: set[str] = set()
        extracted: list[dict] = []
        for t in all_extracted:
            key = t.get("term", "").strip().lower()
            if key and key not in seen_terms:
                seen_terms.add(key)
                extracted.append(t)
    except Exception as e:
        logger.warning("Handbook term extraction failed: %s", e)
        await _log_stage(
            supabase, run_id, "handbook.extract", "failed", t0,
            error_message=str(e),
        )
        return 0, [f"Term extraction failed: {e}"]

    await _log_stage(
        supabase, run_id, "handbook.extract", "success", t0,
        input_summary=f"{len(article_texts)} articles, {len(combined)} chars",
        output_summary=f"{len(extracted)} terms extracted (from {len(all_extracted)} raw)",
        usage=total_usage,
        debug_meta={
            "terms": [t.get("term", "") for t in extracted],
        },
    )

    if not extracted:
        return 0, []

    # Step 2: Filter, dedup, and generate content for new terms (2 at a time)
    VALID_CATEGORIES = {
        "cs-fundamentals", "math-statistics", "ml-fundamentals",
        "deep-learning", "llm-genai", "data-engineering",
        "infra-hardware", "safety-ethics", "products-platforms",
    }

    # Blocklist: terms that passed LLM extraction but are not handbook-worthy
    # (outcome/strategy phrases, industry names, overly generic terms)
    TERM_BLOCKLIST = {
        "ecosystem integration", "cross-platform ai", "dynamic content delivery",
        "content recommendations", "photorealistic graphics", "image generation",
        "gaming industry", "collaboration", "actionable intelligence",
        "ai-driven efficiencies", "cost efficiency", "administrative tasks",
        "collaborative healthcare", "precision health", "legacy infrastructure",
        "warping operation", "self-editing context",
        "variation operator", "verification-centric agents",
    }

    # Generic suffix patterns that indicate outcome/strategy phrases, not technology
    GENERIC_SUFFIXES = (
        " integration", " optimization", " management", " delivery",
        " efficiencies", " operations", " intelligence", " industry",
    )

    # Pre-filter terms before generation
    valid_terms: list[dict] = []
    queued_terms: list[dict] = []
    for term_info in extracted:
        term_name = term_info.get("term", "").strip()
        korean_name = term_info.get("korean_name", "").strip()
        if not term_name:
            continue

        # Scope gate (Task A.4): HR/regulatory/out-of-scope/product-without-allowlist
        # rejection. Runs before every other filter (beyond the empty-term guard) so
        # the rejection reason is the earliest, most specific signal we can log.
        scope_ok, scope_reason = validate_term_scope(
            term_name,
            term_type=term_info.get("term_type"),
        )
        if not scope_ok:
            logger.info("Rejecting out-of-scope term '%s': %s", term_name, scope_reason)
            try:
                supabase.table("pipeline_logs").insert({
                    "run_id": run_id,
                    "pipeline_type": "handbook.scope_gate",
                    "status": "skipped",
                    "debug_meta": {
                        "event": "handbook_term_rejected",
                        "term": term_name,
                        "term_type": term_info.get("term_type"),
                        "reason": scope_reason,
                    },
                }).execute()
            except Exception as _log_err:
                logger.warning(
                    "pipeline_logs insert for rejected term failed (non-fatal): %s",
                    _log_err,
                )
            continue

        if len(term_name.split()) > 3:
            logger.info("Skipping '%s' — too many words", term_name)
            continue
        lower = term_name.lower()
        modifier_suffixes = ("-powered", "-driven", "-based", "-enabled", "-oriented", "-focused", "-first")
        if any(s in lower for s in modifier_suffixes):
            logger.info("Skipping '%s' — adjective/modifier", term_name)
            continue
        # Blocklist check
        if lower in TERM_BLOCKLIST:
            logger.info("Skipping '%s' — blocklisted (not handbook-worthy)", term_name)
            continue
        # Generic suffix check (catches "X integration", "Y optimization" patterns)
        if any(lower.endswith(s) for s in GENERIC_SUFFIXES):
            # Allow known exceptions (e.g., "query optimization" is a real DB concept)
            known_exceptions = {
                "query optimization", "gradient optimization", "kernel optimization",
                "workflow orchestration", "access management", "memory management",
                "process management", "dependency management", "package management",
            }
            if lower not in known_exceptions:
                logger.info("Skipping '%s' — generic suffix pattern", term_name)
                continue
        # Build categories list from primary + secondary
        primary_cat = term_info.get("category", "")
        if primary_cat not in VALID_CATEGORIES:
            logger.info("Skipping '%s' — invalid category '%s'", term_name, primary_cat)
            continue
        secondary = term_info.get("secondary_categories", []) or []
        all_cats = [primary_cat] + [c for c in secondary if c in VALID_CATEGORIES and c != primary_cat]
        slug = _slugify(term_name)
        if not slug:
            continue

        # Check if term already exists (3-layer dedup: slug, exact term, abbreviation)
        try:
            exists_by_slug = supabase.table("handbook_terms").select("id").eq("slug", slug).limit(1).execute()
            if exists_by_slug.data:
                logger.info("Handbook term '%s' already exists (slug match), skipping", term_name)
                continue
            exists_by_term = supabase.table("handbook_terms").select("id").ilike("term", term_name).limit(1).execute()
            if exists_by_term.data:
                logger.info("Handbook term '%s' already exists (term match), skipping", term_name)
                continue
            # Abbreviation check: "RAG (Retrieval-Augmented Generation)" → check if "RAG" exists
            short_name = term_name.split("(")[0].strip()
            if short_name != term_name and len(short_name) >= 2:
                exists_by_short = supabase.table("handbook_terms").select("id, term").ilike("term", f"{short_name}%").limit(5).execute()
                if exists_by_short.data:
                    existing = exists_by_short.data[0]["term"]
                    logger.info("Handbook term '%s' already exists as '%s' (abbreviation match), skipping", term_name, existing)
                    continue
            # Reverse abbreviation: "Retrieval-Augmented Generation" → extract initials "RAG" → check DB
            words = term_name.replace("-", " ").split()
            if len(words) >= 2:
                initials = "".join(w[0] for w in words if w[0].isupper())
                if len(initials) >= 3:  # min 3 chars to avoid false positives (ME, AI, etc.)
                    exists_by_initials = supabase.table("handbook_terms").select("id, term").ilike("term", initials).limit(1).execute()
                    if exists_by_initials.data:
                        existing = exists_by_initials.data[0]["term"]
                        logger.info("Handbook term '%s' already exists as '%s' (initials match), skipping", term_name, existing)
                        continue
        except Exception as e:
            logger.warning("Duplicate check failed for '%s': %s", term_name, e)
            continue

        confidence = term_info.get("confidence", "high")
        term_payload = {
            "term": term_name,
            "korean_name": korean_name,
            "slug": slug,
            "categories": all_cats,
            "category": primary_cat,
            "secondary_categories": secondary,
            "reason": term_info.get("reason", "").strip(),
        }
        if confidence == "low":
            queued_terms.append(term_payload)
            logger.info("Queuing low-confidence term '%s' for manual review", term_name)
        else:
            valid_terms.append(term_payload)

    # Semantic dedup within batch: remove terms that overlap with others
    def _term_words(name: str) -> set[str]:
        """Extract significant words from a term name for similarity comparison."""
        # General stop words + domain-common words too generic to signal similarity
        stop = {
            "the", "a", "an", "of", "in", "for", "and", "or", "with", "on", "to",
            "ai", "ml", "gpu", "cpu", "model", "system", "based", "deep", "large",
        }
        return {w for w in name.lower().replace("-", " ").split() if w not in stop and len(w) > 1}

    def _is_semantic_dup(term_a: str, term_b: str) -> bool:
        """Check if two terms are semantically overlapping."""
        slug_a, slug_b = _slugify(term_a), _slugify(term_b)
        # One slug contains the other (e.g., "attention" vs "grouped-query attention")
        if slug_a in slug_b or slug_b in slug_a:
            return True
        # High word overlap (e.g., "agentic model" vs "agentic AI")
        words_a, words_b = _term_words(term_a), _term_words(term_b)
        if not words_a or not words_b:
            return False
        overlap = words_a & words_b
        if not overlap:
            return False
        smaller = min(len(words_a), len(words_b))
        if smaller <= 1:
            # Both terms have only 1 significant word and it's the same
            # e.g., "agentic model" (→ {"agentic"}) vs "agentic AI" (→ {"agentic"})
            return words_a == words_b and len(words_a) == 1
        return len(overlap) / smaller >= 0.5

    # Deduplicate valid_terms: keep the first (higher priority from LLM ordering)
    deduped_valid: list[dict] = []
    for term_info in valid_terms:
        term_name = term_info["term"]
        is_dup = False
        for existing_info in deduped_valid:
            existing_name = existing_info["term"]
            if _is_semantic_dup(term_name, existing_name):
                logger.info("Skipping '%s' — semantic duplicate of '%s'", term_name, existing_name)
                is_dup = True
                break
        if not is_dup:
            deduped_valid.append(term_info)
    valid_terms = deduped_valid

    # LLM gate: verify candidates against existing handbook terms before expensive generation
    if valid_terms:
        try:
            existing = supabase.table("handbook_terms").select("term").neq("status", "archived").execute()
            existing_names = [r["term"] for r in (existing.data or [])]
            gate_candidates = [
                {
                    "term": term_info["term"],
                    "korean_name": term_info["korean_name"],
                    "category": term_info.get("category", ""),
                    "secondary_categories": term_info.get("secondary_categories", []),
                    "reason": term_info.get("reason", ""),
                }
                for term_info in valid_terms
            ]
            gate_results = await gate_candidate_terms(gate_candidates, existing_names)
            decisions = {
                result["term"]: result
                for result in gate_results
                if result.get("term")
            }
            accepted_terms: list[dict] = []
            queued_from_gate = 0
            rejected_count = 0
            for term_info in valid_terms:
                decision_info = decisions.get(term_info["term"], {})
                decision = str(decision_info.get("decision", "accept")).lower()
                reason = decision_info.get("reason", "")
                if decision == "reject":
                    rejected_count += 1
                    logger.info("LLM gate rejected '%s': %s", term_info["term"], reason or "no reason")
                    continue
                if decision == "queue":
                    queued_from_gate += 1
                    queued_terms.append(term_info)
                    logger.info("LLM gate queued '%s': %s", term_info["term"], reason or "no reason")
                    continue
                accepted_terms.append(term_info)

            valid_terms = accepted_terms
            if rejected_count or queued_from_gate:
                logger.info(
                    "LLM gate filtered %d/%d candidates (%d queued, %d rejected)",
                    queued_from_gate + rejected_count,
                    len(gate_candidates),
                    queued_from_gate,
                    rejected_count,
                )
        except Exception as e:
            logger.warning("LLM gate failed, proceeding with all candidates: %s", e)

    # Generate terms concurrently (max 2 at a time)
    sem = asyncio.Semaphore(2)
    pipeline_start = time.monotonic()
    PIPELINE_TIMEOUT_SEC = 30 * 60  # 30 minutes max for entire handbook pipeline

    TERM_TIMEOUT_SEC = 10 * 60  # 10 minutes max per single term generation

    async def _create_single_term(term_name: str, korean_name: str, slug: str, categories: list[str] | None = None) -> tuple[int, list[str]]:
        """Generate and save a single handbook term. Returns (created_count, errors)."""
        # Check pipeline-level timeout before starting a new term
        elapsed = time.monotonic() - pipeline_start
        if elapsed > PIPELINE_TIMEOUT_SEC:
            msg = f"Handbook pipeline timeout ({int(elapsed)}s) — skipping '{term_name}'"
            logger.warning(msg)
            return 0, [msg]
        async with sem:
            # Filter to articles that mention this specific term
            relevant = [a for a in article_texts if term_name.lower() in a.lower()]
            term_context = "\n\n---\n\n".join(relevant)[:4000] if relevant else combined[:4000]

            t_gen = time.monotonic()
            try:
                content_data, gen_usage = await asyncio.wait_for(
                    generate_term_content(
                        term_name, korean_name,
                        article_context=term_context,
                        categories=categories,
                    ),
                    timeout=TERM_TIMEOUT_SEC,
                )
            except asyncio.TimeoutError:
                error_msg = f"Handbook generate timed out for '{term_name}' ({TERM_TIMEOUT_SEC}s)"
                logger.warning(error_msg)
                await _log_stage(
                    supabase, run_id, "handbook.auto_generate", "failed", t_gen,
                    error_message=error_msg,
                    debug_meta={"term": term_name, "source": "pipeline", "timeout": True},
                )
                return 0, [error_msg]
            except Exception as e:
                error_msg = f"Handbook generate failed for '{term_name}': {e}"
                logger.warning(error_msg)
                await _log_stage(
                    supabase, run_id, "handbook.auto_generate", "failed", t_gen,
                    error_message=error_msg,
                    debug_meta={"term": term_name, "source": "pipeline"},
                )
                return 0, [error_msg]

            # Extract quality warnings propagated from advisor
            warnings = content_data.pop("_warnings", [])
            _queue_triggers = ("quality score", "unverified entit", "section", "empty", "needs_review")
            term_status = "queued" if any(
                any(trigger in w.lower() for trigger in _queue_triggers)
                for w in warnings
            ) else "draft"

            # Korean name gate (Task C.4): if korean_name looks invented or missing
            # the required Hangul minimum, queue this term for Amy's manual
            # Korean-only review. Term body is still saved — only the korean_name
            # needs fixing, so we don't want to waste the 50+s of body generation.
            korean_name_final = content_data.get("korean_name", korean_name)
            korean_ok, korean_reason = validate_korean_name(term_name, korean_name_final)
            if not korean_ok:
                term_status = "queued"
                logger.info(
                    "Queuing term '%s' for Korean-name review: %s",
                    term_name, korean_reason,
                )
                try:
                    supabase.table("pipeline_logs").insert({
                        "run_id": run_id,
                        "pipeline_type": "handbook.korean_gate",
                        "status": "queued",
                        "debug_meta": {
                            "event": "handbook_korean_name_queued",
                            "term": term_name,
                            "korean_name": korean_name_final,
                            "reason": korean_reason,
                        },
                    }).execute()
                except Exception as _log_err:
                    logger.warning(
                        "pipeline_logs insert for queued Korean review failed (non-fatal): %s",
                        _log_err,
                    )

            # Entity grounding gate (Task B.2): if the term never appears verbatim
            # in any of the source articles, queue it for Amy's review — may be
            # legitimately new, may be fabricated from fragments.
            grounding_ok, grounding_reason = validate_term_grounding(term_name, article_texts)
            if not grounding_ok:
                term_status = "queued"
                logger.info(
                    "Queuing term '%s' for grounding review: %s",
                    term_name, grounding_reason,
                )
                try:
                    supabase.table("pipeline_logs").insert({
                        "run_id": run_id,
                        "pipeline_type": "handbook.grounding_gate",
                        "status": "queued",
                        "debug_meta": {
                            "event": "handbook_term_ungrounded",
                            "term": term_name,
                            "reason": grounding_reason,
                        },
                    }).execute()
                except Exception as _log_err:
                    logger.warning(
                        "pipeline_logs insert for ungrounded term failed (non-fatal): %s",
                        _log_err,
                    )

            try:
                row = {
                    "term": term_name,
                    "slug": slug,
                    "korean_name": content_data.get("korean_name", korean_name),
                    "term_full": content_data.get("term_full", ""),
                    "korean_full": content_data.get("korean_full", ""),
                    "categories": content_data.get("categories", []),
                    "summary_ko": content_data.get("summary_ko", ""),
                    "summary_en": content_data.get("summary_en", ""),
                    "definition_ko": content_data.get("definition_ko", ""),
                    "definition_en": content_data.get("definition_en", ""),
                    "body_basic_ko": content_data.get("body_basic_ko", ""),
                    "body_basic_en": content_data.get("body_basic_en", ""),
                    "body_advanced_ko": content_data.get("body_advanced_ko", ""),
                    "body_advanced_en": content_data.get("body_advanced_en", ""),
                    "hero_news_context_ko": content_data.get("hero_news_context_ko", ""),
                    "hero_news_context_en": content_data.get("hero_news_context_en", ""),
                    "references_ko": content_data.get("references_ko", []),
                    "references_en": content_data.get("references_en", []),
                    "term_type": content_data.get("term_type", ""),
                    "facet_intent": content_data.get("facet_intent", []),
                    "facet_volatility": content_data.get("facet_volatility", "stable"),
                    "status": term_status,
                    "source": "pipeline",
                }
                result = supabase.table("handbook_terms").insert(row).execute()
                if not result.data:
                    error_msg = f"Insert returned empty for '{term_name}'"
                    logger.error(error_msg)
                    await _log_stage(
                        supabase, run_id, "handbook.auto_generate", "failed", t_gen,
                        error_message=error_msg, usage=gen_usage,
                        debug_meta={"term": term_name, "slug": slug, "source": "pipeline"},
                    )
                    return 0, [error_msg]

                new_term_id = result.data[0].get("id") if result.data else None
                logger.info("Created handbook draft: %s (%s) id=%s", term_name, slug, new_term_id)

                # P2-4: Link quality_scores to the newly created term
                if new_term_id:
                    try:
                        supabase.table("handbook_quality_scores").update(
                            {"term_id": new_term_id}
                        ).eq("term_slug", term_name).is_("term_id", "null").execute()
                    except Exception:
                        pass  # best-effort linking

                await _log_stage(
                    supabase, run_id, "handbook.auto_generate", "success", t_gen,
                    output_summary=f"term={term_name}, slug={slug}",
                    debug_meta={"term": term_name, "slug": slug, "source": "pipeline", "term_id": new_term_id},
                )
                return 1, []
            except Exception as e:
                error_msg = f"Failed to save handbook term '{term_name}': {e}"
                logger.error(error_msg)
                await _log_stage(
                    supabase, run_id, "handbook.auto_generate", "failed", t_gen,
                    error_message=error_msg,
                    debug_meta={"term": term_name, "slug": slug, "source": "pipeline"},
                )
                return 0, [error_msg]

    if valid_terms:
        term_results = await asyncio.gather(
            *[
                _create_single_term(
                    term_info["term"],
                    term_info["korean_name"],
                    term_info["slug"],
                    term_info.get("categories"),
                )
                for term_info in valid_terms
            ],
        )
        for created, term_errors in term_results:
            terms_created += created
            errors.extend(term_errors)

    # Save low-confidence terms as queued (title only, no LLM generation)
    queued_count = 0
    for term_info in queued_terms:
        term_name = term_info["term"]
        korean_name = term_info["korean_name"]
        slug = term_info["slug"]
        cats = term_info.get("categories", [])
        try:
            supabase.table("handbook_terms").insert({
                "term": term_name,
                "slug": slug,
                "korean_name": korean_name,
                "categories": cats,
                "status": "queued",
                "source": "pipeline",
            }).execute()
            queued_count += 1
            logger.info("Queued handbook term for review: %s (%s)", term_name, slug)
        except Exception as e:
            logger.warning("Failed to queue term '%s': %s", term_name, e)

    logger.info(
        "Handbook auto-extraction: %d created, %d queued for review, %d errors",
        terms_created, queued_count, len(errors),
    )
    return terms_created, errors


# _strip_empty_sections, _fix_bold_spacing, _clean_writer_output,
# _extract_digest_items, _map_digest_items_to_group_indexes,
# _generate_digest → moved to pipeline_digest.py


async def run_daily_pipeline(
    batch_id: str | None = None,
    target_date: str | None = None,
    skip_handbook: bool = False,
    force_fresh: bool = False,
    auto_publish: bool = False,
) -> PipelineResult:
    """Run the full daily AI news pipeline.

    Flow: collect → rank → (react + extract + personas) × 2 → save drafts.
    """
    if batch_id is None:
        batch_id = target_date or today_kst()

    is_backfill = False
    if target_date:
        try:
            is_backfill = datetime.strptime(target_date, "%Y-%m-%d").date() < datetime.strptime(today_kst(), "%Y-%m-%d").date()
        except ValueError:
            pass

    supabase = get_supabase()
    if not supabase:
        return PipelineResult(
            batch_id=batch_id,
            errors=["Supabase not configured"],
        )

    total_posts = 0
    all_errors: list[str] = []
    cumulative_usage: dict[str, Any] = {}

    run_key = f"news-{batch_id}"
    try:
        # Reuse existing run or create new
        _res = supabase.table("pipeline_runs").select("id, status").eq("run_key", run_key).limit(1).execute()
        existing = _res.data[0] if _res.data else None
        if existing:
            run_id = existing["id"]
            if force_fresh:
                # Manual "Run Pipeline": wipe logs and start from scratch
                supabase.table("pipeline_logs").delete().eq("run_id", run_id).execute()
                logger.info("Force-fresh: cleared logs for %s", run_key)
            else:
                # Cron retry: preserve logs (checkpoints) for "Rerun from..." support
                logger.info("Reusing news run %s, preserving logs (was %s)", run_key, existing["status"])
            supabase.table("pipeline_runs").update({
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "finished_at": None,
                "last_error": None,
            }).eq("id", run_id).execute()
        else:
            run_id = str(uuid.uuid4())
            supabase.table("pipeline_runs").insert({
                "id": run_id,
                "run_key": run_key,
                "status": "running",
            }).execute()
    except Exception as e:
        logger.error("Pipeline run setup failed for %s: %s", batch_id, e)
        raise

    try:
        # Fetch recently published source URLs + headlines to avoid repeating news
        published_urls: set[str] = set()
        recent_headlines: list[str] = []
        try:
            # URL exclusion: published only (draft URLs shouldn't block collection)
            recent = supabase.table("news_posts").select("source_urls") \
                .eq("status", "published") \
                .gte("published_at", (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()) \
                .execute()
            for row in (recent.data or []):
                for url in (row.get("source_urls") or []):
                    published_urls.add(url)
            # Headlines for event dedup: draft + published (any generated post counts)
            cutoff_2d = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
            headline_rows = supabase.table("news_posts").select("title") \
                .in_("status", ["published", "draft"]) \
                .gte("published_at", cutoff_2d) \
                .execute()
            recent_headlines = [
                row["title"] for row in (headline_rows.data or [])
                if row.get("title")
            ]
        except Exception as e:
            logger.warning("Failed to fetch published URLs/headlines: %s", e)

        # Stage: collect
        t0 = time.monotonic()
        candidates, collect_meta = await collect_news(
            target_date=target_date,
            published_urls=published_urls,
        )

        await _log_stage(
            supabase, run_id, "collect", "success" if candidates else "no_news", t0,
            input_summary=f"target_date={target_date or 'today'}",
            output_summary=f"{len(candidates)} unique candidates",
            debug_meta={
                "target_date": target_date,
                "is_backfill": is_backfill,
                "mode": "backfill" if is_backfill else "daily",
                **collect_meta,
            },
        )
        _save_checkpoint(supabase, run_id, "collect", {
            "candidates": [c.model_dump() for c in candidates],
        })

        if not candidates:
            logger.info("No news candidates found, pipeline complete")
            try:
                supabase.table("pipeline_runs").update({
                    "status": "success",
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "last_error": None,
                }).eq("id", run_id).execute()
            except Exception as e:
                logger.warning("Failed to update pipeline run: %s", e)
            return PipelineResult(batch_id=batch_id)

        # Stage: classify (individual article selection)
        t0 = time.monotonic()
        classification, classify_usage, classify_user_prompt = await classify_candidates(
            candidates, recent_headlines=recent_headlines,
        )
        cumulative_usage = merge_usage_metrics(cumulative_usage, classify_usage)

        # Fallback: if aggressive dedup rejected every candidate, retry without
        # the ALREADY COVERED block. Slow news days + overlapping time windows
        # can trigger false-positive dedup — better to publish 2-3 items than
        # zero. See vault/09-Implementation/plans notes on 2026-04-19 incident.
        classify_fallback_used = False
        if not classification.research_picks and not classification.business_picks:
            logger.warning(
                "Classify returned 0 picks with dedup block; retrying without ALREADY COVERED (fallback mode)"
            )
            fallback_classification, fallback_usage, fallback_prompt = await classify_candidates(
                candidates, recent_headlines=None,
            )
            cumulative_usage = merge_usage_metrics(cumulative_usage, fallback_usage)
            classification = fallback_classification
            classify_user_prompt = fallback_prompt
            classify_fallback_used = True

        # Code-level dedup safety net: even if the LLM ignored the ALREADY COVERED
        # block, drop candidates whose entity tokens (company + product) overlap
        # heavily with recent headlines. This is a deterministic guard.
        # Skipped in fallback mode — the whole point of fallback is to allow
        # some overlap rather than publish nothing.
        dedup_dropped: list[str] = []
        if recent_headlines and not classify_fallback_used:
            classification, dedup_dropped = _filter_recent_duplicates(classification, recent_headlines)
            if dedup_dropped:
                logger.warning("Code-level dedup dropped %d candidate(s): %s",
                               len(dedup_dropped), "; ".join(dedup_dropped)[:300])

        # Use the EXACT user_prompt the LLM saw (includes ALREADY COVERED block).
        # This is the only reliable way to debug dedup behavior.
        classify_input_summary = classify_user_prompt
        classify_output = {
            "research": [
                {"title": c.title, "url": c.url, "subcategory": c.subcategory}
                for c in classification.research_picks
            ],
            "business": [
                {"title": c.title, "url": c.url, "subcategory": c.subcategory}
                for c in classification.business_picks
            ],
        }

        classify_warnings = _check_pipeline_health(
            "classify",
            classify_picks=(len(classification.research_picks), len(classification.business_picks)),
        )
        for w in classify_warnings:
            logger.warning("Health check: %s", w)

        await _log_stage(
            supabase, run_id, "classify", "success", t0,
            input_summary=f"{len(candidates)} candidates",
            output_summary=f"research={len(classification.research_picks)} picks, business={len(classification.business_picks)} picks",
            usage=classify_usage,
            debug_meta={
                "llm_input": _trim(classify_input_summary),
                "llm_output": classify_output,
                "candidates_count": len(candidates),
                "warnings": classify_warnings,
                "dedup_dropped": dedup_dropped,
                "recent_headlines_count": len(recent_headlines),
                "fallback_used": classify_fallback_used,
            },
        )
        _save_checkpoint(supabase, run_id, "classify", {
            "research_picks": [c.model_dump() for c in classification.research_picks],
            "business_picks": [c.model_dump() for c in classification.business_picks],
        })

        # Stage: merge (group same-event articles from full candidate pool)
        t0 = time.monotonic()
        classification, merge_usage = await merge_classified(classification, candidates)
        cumulative_usage = merge_usage_metrics(cumulative_usage, merge_usage)

        merge_output = {
            "research": [
                {"group_title": g.group_title, "items": [i.url for i in g.items], "subcategory": g.subcategory}
                for g in classification.research
            ],
            "business": [
                {"group_title": g.group_title, "items": [i.url for i in g.items], "subcategory": g.subcategory}
                for g in classification.business
            ],
        }
        all_merged = classification.research + classification.business
        merge_warnings = _check_pipeline_health("merge", merge_groups=all_merged)
        for w in merge_warnings:
            logger.warning("Health check: %s", w)

        await _log_stage(
            supabase, run_id, "merge", "success", t0,
            input_summary=f"{len(classification.research_picks)+len(classification.business_picks)} picks + {len(candidates)} candidates",
            output_summary=f"research={len(classification.research)} groups, business={len(classification.business)} groups",
            usage=merge_usage,
            debug_meta={"llm_output": merge_output, "warnings": merge_warnings},
        )
        _save_checkpoint(supabase, run_id, "merge", {
            "research": [g.model_dump() for g in classification.research],
            "business": [g.model_dump() for g in classification.business],
        })

        handbook_slugs = _fetch_handbook_slugs(supabase)
        raw_content_map = {c.url: c.raw_content for c in candidates if c.raw_content}

        # Stage: community reactions (all grouped items, deduplicated)
        t0 = time.monotonic()
        all_classified = classification.research + classification.business
        seen_community_urls: set[str] = set()
        community_lookup: list[tuple[str, str]] = []  # (title, url)
        for group in all_classified:
            # Use group_title for search (better keywords than raw item titles like GitHub repo names)
            search_title = group.group_title
            for item in group.items:
                if item.url not in seen_community_urls:
                    seen_community_urls.add(item.url)
                    community_lookup.append((search_title, item.url))
        community_map: dict[str, str] = {}
        # Extract date from batch_id (e.g. "news-2026-03-27" → "2026-03-27")
        _target_date = batch_id.replace("news-", "") if batch_id.startswith("news-") else batch_id
        if community_lookup:
            community_tasks = [
                collect_community_reactions(title, url, target_date=_target_date)
                for title, url in community_lookup
            ]
            community_results = await asyncio.gather(*community_tasks, return_exceptions=True)
            for (_, url), result in zip(community_lookup, community_results):
                if isinstance(result, str) and result.strip():
                    community_map[url] = result

        community_warnings = _check_pipeline_health(
            "community",
            community_total=len(community_lookup),
            community_found=len(community_map),
        )
        for w in community_warnings:
            logger.warning("Health check: %s", w)

        await _log_stage(
            supabase, run_id, "community", "success", t0,
            input_summary=f"{len(community_lookup)} items queried",
            output_summary=f"{len(community_map)} reactions collected",
            debug_meta={"warnings": community_warnings} if community_warnings else None,
        )
        _save_checkpoint(supabase, run_id, "community", {
            "community_map": community_map,
        })

        # Stage: community_summarize (structured insights from raw comments)
        t0 = time.monotonic()
        community_summary_map, community_summarize_usage = await summarize_community(
            community_map, all_classified,
        )
        cumulative_usage = merge_usage_metrics(cumulative_usage, community_summarize_usage)
        await _log_stage(
            supabase, run_id, "community_summarize", "success", t0,
            input_summary=f"{len(community_map)} raw reactions",
            output_summary=f"{len(community_summary_map)} insights produced",
            usage=community_summarize_usage,
        )
        _save_checkpoint(supabase, run_id, "community_summarize", {
            "summaries": {url: ins.model_dump() for url, ins in community_summary_map.items()},
        })

        # Stage: ranking (Lead/Supporting assignment per category)
        t0 = time.monotonic()
        research_ranked, research_rank_usage = await rank_classified(
            classification.research, "research", community_map,
        )
        business_ranked, business_rank_usage = await rank_classified(
            classification.business, "business", community_map,
        )
        classification.research = research_ranked
        classification.business = business_ranked
        rank_usage = merge_usage_metrics(research_rank_usage, business_rank_usage)
        cumulative_usage = merge_usage_metrics(cumulative_usage, rank_usage)

        await _log_stage(
            supabase, run_id, "ranking", "success", t0,
            input_summary=f"research={len(classification.research)}, business={len(classification.business)}",
            output_summary="leads assigned",
            usage=rank_usage,
        )
        _save_checkpoint(supabase, run_id, "rank", {
            "research": [g.model_dump() for g in classification.research],
            "business": [g.model_dump() for g in classification.business],
        })

        # Stage: enrich — find additional sources for groups with 1 item only
        t0 = time.monotonic()
        all_ranked = classification.research + classification.business
        enriched_map = await enrich_sources(
            all_ranked, raw_content_map, target_date=target_date,
        )
        merged_groups = sum(1 for g in all_ranked if len(g.items) >= 2)
        exa_groups = len(all_ranked) - merged_groups
        enrich_warnings = _check_pipeline_health(
            "enrich", enrich_map=enriched_map, all_groups=all_ranked,
        )
        for w in enrich_warnings:
            logger.warning("Health check: %s", w)

        await _log_stage(
            supabase, run_id, "enrich", "success", t0,
            input_summary=f"{len(all_ranked)} groups ({merged_groups} merged, {exa_groups} via Exa)",
            output_summary=f"{sum(len(s) for s in enriched_map.values())} total sources",
            debug_meta={"warnings": enrich_warnings} if enrich_warnings else None,
        )
        _save_checkpoint(supabase, run_id, "enrich", {
            "enriched_map": enriched_map,
            "raw_content_map": {k: v[:15000] for k, v in raw_content_map.items()},
        })

        # Generate research + business digests in parallel
        digest_tasks = []
        for digest_type, classified_items in [
            ("research", classification.research),
            ("business", classification.business),
        ]:
            if not classified_items:
                continue
            digest_tasks.append(
                _generate_digest(
                    classified=classified_items,
                    digest_type=digest_type,
                    batch_id=batch_id,
                    handbook_slugs=handbook_slugs,
                    raw_content_map=raw_content_map,
                    community_summary_map=community_summary_map,
                    supabase=supabase,
                    run_id=run_id,
                    enriched_map=enriched_map,
                    auto_publish=auto_publish,
                )
            )

        digest_results = await asyncio.gather(*digest_tasks, return_exceptions=True)
        for result in digest_results:
            if isinstance(result, Exception):
                all_errors.append(f"Digest generation failed: {result}")
                logger.error("Digest generation exception: %s", result)
            else:
                posts, errors, usage = result
                total_posts += posts
                all_errors.extend(errors)
                cumulative_usage = merge_usage_metrics(cumulative_usage, usage)

        # Stage: summary (news only — handbook runs separately)
        t_summary = time.monotonic()
        status = "success" if total_posts > 0 and not all_errors else "failed"

        await _log_stage(
            supabase, run_id, "summary", status, t_summary,
            input_summary=f"{len(candidates)} candidates",
            output_summary=f"{total_posts} posts created",
            usage=cumulative_usage,
            error_message="; ".join(all_errors) if all_errors else None,
            debug_meta={
                "mode": "backfill" if is_backfill else "daily",
                "target_date": target_date,
                "batch_id": batch_id,
                "total_posts": total_posts,
                "total_cost": cumulative_usage.get("cost_usd"),
                "research_count": len(classification.research),
                "business_count": len(classification.business),
            },
        )

        try:
            supabase.table("pipeline_runs").update({
                "status": status,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "last_error": all_errors[0] if all_errors else None,
            }).eq("id", run_id).execute()
        except Exception as e:
            logger.warning("Failed to update pipeline run: %s", e)

    except Exception as e:
        logger.error("Pipeline unexpected error: %s", e)
        all_errors.append(str(e))
        try:
            supabase.table("pipeline_runs").update({
                "status": "failed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "last_error": str(e),
            }).eq("id", run_id).execute()
        except Exception:
            pass

    result = PipelineResult(
        batch_id=batch_id,
        posts_created=total_posts,
        errors=all_errors,
        usage=cumulative_usage,
    )
    logger.info("News pipeline complete: %d posts, %d errors", total_posts, len(all_errors))

    # Auto-trigger handbook extraction as a separate run (non-blocking)
    expected_posts = 4  # research(en,ko) + business(en,ko)
    if total_posts >= expected_posts and not skip_handbook:
        try:
            await run_handbook_extraction(batch_id)
        except Exception as e:
            logger.warning("Handbook extraction auto-trigger failed: %s", e)
    elif total_posts > 0 and not skip_handbook:
        logger.warning(
            "Skipping handbook extraction: only %d/%d posts created (errors: %s)",
            total_posts, expected_posts, all_errors[:3],
        )

    return result


def _load_personas_and_frontload_from_db(
    supabase, batch_id: str,
) -> tuple[dict[str, dict[str, "PersonaOutput"]], dict[str, dict[str, Any]]]:
    """Reconstruct per-digest-type PersonaOutput + frontload from existing news_posts rows.

    Used by rerun_from='quality' to re-run QC without regenerating content.
    Returns:
        personas_by_type: {"research": {"expert": PersonaOutput, "learner": PersonaOutput}, "business": {...}}
        frontload_by_type: {"research": {headline, headline_ko, excerpt, excerpt_ko, focus_items, focus_items_ko}, "business": {...}}
    """
    slugs = [
        f"{batch_id.lower()}-research-digest",
        f"{batch_id.lower()}-research-digest-ko",
        f"{batch_id.lower()}-business-digest",
        f"{batch_id.lower()}-business-digest-ko",
    ]
    resp = (
        supabase.table("news_posts")
        .select("slug,locale,post_type,content_expert,content_learner,title,excerpt,focus_items,guide_items")
        .eq("category", "ai-news")
        .in_("slug", slugs)
        .execute()
    )
    rows = resp.data or []

    # Group rows by digest_type
    by_type: dict[str, dict[str, dict]] = {}  # {type: {locale: row}}
    for row in rows:
        dtype = row.get("post_type")
        loc = row.get("locale")
        if dtype in ("research", "business") and loc in ("en", "ko"):
            by_type.setdefault(dtype, {})[loc] = row

    personas_by_type: dict[str, dict[str, PersonaOutput]] = {}
    frontload_by_type: dict[str, dict[str, Any]] = {}

    for dtype, by_loc in by_type.items():
        en_row = by_loc.get("en") or {}
        ko_row = by_loc.get("ko") or {}

        personas_by_type[dtype] = {
            "expert": PersonaOutput(
                en=en_row.get("content_expert") or "",
                ko=ko_row.get("content_expert") or "",
            ),
            "learner": PersonaOutput(
                en=en_row.get("content_learner") or "",
                ko=ko_row.get("content_learner") or "",
            ),
        }

        # Frontload: EN fields from EN row, KO from KO row, focus_items_ko from KO row's focus_items
        guide = en_row.get("guide_items") or {}
        frontload_by_type[dtype] = {
            "headline": en_row.get("title") or "",
            "headline_ko": ko_row.get("title") or guide.get("title_learner") or "",
            "excerpt": en_row.get("excerpt") or "",
            "excerpt_ko": ko_row.get("excerpt") or guide.get("excerpt_learner") or "",
            "focus_items": en_row.get("focus_items") or [],
            "focus_items_ko": ko_row.get("focus_items") or [],
        }

    return personas_by_type, frontload_by_type


async def rerun_pipeline_stage(
    source_run_id: str,
    from_stage: str,
    batch_id: str,
    category: str | None = None,
) -> PipelineResult:
    """Rerun pipeline from a specific stage using saved checkpoints.

    Reuses the existing pipeline_run (source_run_id) — deletes logs from
    the rerun stage onward, then re-executes those stages in place.

    Args:
        source_run_id: Run ID to rerun (and load checkpoints from).
        from_stage: Stage to start from ("classify"|"merge"|"community"|"write").
        batch_id: Target date (YYYY-MM-DD).
        category: "research"|"business"|None (both).
    """
    from models.news_pipeline import ClassifiedCandidate, NewsCandidate

    supabase = get_supabase()
    run_id = source_run_id  # Reuse existing run

    # Delete logs from the rerun stage onward
    STAGE_CASCADE = {
        "classify": ["classify", "merge", "community", "community_summarize", "ranking", "enrich",
                      "digest:research:expert", "digest:research:learner",
                      "digest:business:expert", "digest:business:learner",
                      "quality:research", "quality:business",
                      "save:research", "save:business", "summary"],
        "merge": ["merge", "community", "community_summarize", "ranking", "enrich",
                  "digest:research:expert", "digest:research:learner",
                  "digest:business:expert", "digest:business:learner",
                  "quality:research", "quality:business",
                  "save:research", "save:business", "summary"],
        "community": ["community", "community_summarize", "ranking", "enrich",
                      "digest:research:expert", "digest:research:learner",
                      "digest:business:expert", "digest:business:learner",
                      "quality:research", "quality:business",
                      "save:research", "save:business", "summary"],
        "write": ["digest:research:expert", "digest:research:learner",
                  "digest:business:expert", "digest:business:learner",
                  "quality:research", "quality:business",
                  "save:research", "save:business", "summary"],
        "quality": ["quality:research", "quality:business",
                    "save:research", "save:business", "summary"],
    }
    stages_to_delete = STAGE_CASCADE.get(from_stage, [])
    # If category filter is set, only delete logs for that category's stages
    if category:
        stages_to_delete = [s for s in stages_to_delete if category in s or ":" not in s or s == "summary"]
    try:
        # Compare-and-set lock: only claim the run if it's NOT already running.
        # This prevents concurrent reruns (double-click, frontend retry, etc.)
        # from both deleting+recreating logs and producing duplicate entries.
        claim_result = (
            supabase.table("pipeline_runs")
            .update({
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "finished_at": None,
                "last_error": None,
            })
            .eq("id", run_id)
            .neq("status", "running")
            .execute()
        )
        if not claim_result.data:
            # Another rerun already has the lock; abort silently so we don't
            # interfere with the in-progress run.
            logger.warning(
                "Rerun for run_id=%s rejected — another rerun already running",
                run_id,
            )
            return PipelineResult(
                batch_id=batch_id,
                status="failed",
                errors=["Another rerun is already running for this batch"],
            )
        # Lock acquired — safe to delete old logs and re-execute stages
        for stage_name in stages_to_delete:
            supabase.table("pipeline_logs").delete().eq("run_id", run_id).eq("pipeline_type", stage_name).execute()
    except Exception as e:
        return PipelineResult(batch_id=batch_id, status="failed", message=f"Failed to prepare rerun: {e}")

    cumulative_usage: dict[str, Any] = {}
    all_errors: list[str] = []
    total_posts = 0

    try:
        # Guard: prevent rerun from overwriting published posts
        published = supabase.table("news_posts").select("id").eq(
            "pipeline_batch_id", batch_id,
        ).eq("status", "published").execute()
        if published.data:
            msg = f"Cannot rerun: {len(published.data)} published posts exist for {batch_id}. Unpublish first."
            logger.error(msg)
            supabase.table("pipeline_runs").update({
                "status": "failed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "last_error": msg,
            }).eq("id", source_run_id).execute()
            return PipelineResult(batch_id=batch_id, status="failed", errors=[msg])

        # --- Branch: quality-only rerun (skip writer + collect/enrich chain) ---
        # When only QC prompts/weights changed, re-score existing news_posts without
        # regenerating content. Loads merge + community_summarize checkpoints for
        # structural checks and personas/frontload from news_posts for the LLM scorer.
        if from_stage == "quality":
            # Need classification (for structural checks) + community summaries
            merge_data = _load_checkpoint(supabase, source_run_id, "merge")
            classification = ClassificationResult()
            if merge_data:
                classification.research = [ClassifiedGroup(**g) for g in merge_data.get("research", [])]
                classification.business = [ClassifiedGroup(**g) for g in merge_data.get("business", [])]

            cs_data = _load_checkpoint(supabase, source_run_id, "community_summarize")
            community_summary_map: dict[str, CommunityInsight] = {}
            if cs_data and cs_data.get("summaries"):
                community_summary_map = {
                    url: CommunityInsight(**ins_data)
                    for url, ins_data in cs_data["summaries"].items()
                }

            personas_by_type, frontload_by_type = _load_personas_and_frontload_from_db(supabase, batch_id)
            if not personas_by_type:
                msg = f"No news_posts found for batch {batch_id} — nothing to rescore"
                all_errors.append(msg)
                await _log_stage(
                    supabase, run_id, "summary", "failed", time.monotonic(),
                    input_summary=f"rerun from {from_stage}" + (f" ({category})" if category else ""),
                    output_summary="0 rows rescored",
                    usage=cumulative_usage,
                    error_message=msg,
                )
                supabase.table("pipeline_runs").update({
                    "status": "failed",
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "last_error": msg,
                }).eq("id", run_id).execute()
                return PipelineResult(
                    batch_id=batch_id,
                    status="failed",
                    posts_created=0,
                    errors=all_errors,
                    usage=cumulative_usage,
                )

            for digest_type in ("research", "business"):
                if category and digest_type != category:
                    continue
                if digest_type not in personas_by_type:
                    continue

                classified_items = getattr(classification, digest_type, []) or []
                personas = personas_by_type[digest_type]
                frontload = frontload_by_type.get(digest_type, {})

                try:
                    qc_result = await _check_digest_quality(
                        personas=personas,
                        digest_type=digest_type,
                        classified=classified_items,
                        community_summary_map=community_summary_map,
                        supabase=supabase,
                        run_id=run_id,
                        cumulative_usage=cumulative_usage,
                        frontload=frontload,
                    )
                except Exception as e:
                    all_errors.append(f"Quality rescore failed for {digest_type}: {e}")
                    continue

                if not isinstance(qc_result, dict):
                    # _check_digest_quality returns a non-dict sentinel (e.g., 0) when it
                    # early-exits due to missing inputs — skip the update in that case.
                    all_errors.append(
                        f"Quality rescore for {digest_type} returned non-dict "
                        f"({type(qc_result).__name__}) — likely missing expert content; skipping update"
                    )
                    continue

                score_int = int(qc_result.get("score") or qc_result.get("quality_score") or 0)
                flags = qc_result.get("quality_flags") or []
                content_analysis = {
                    "scores_breakdown": qc_result.get("quality_breakdown"),
                    "issues": qc_result.get("quality_issues") or [],
                }
                analyzed_at = datetime.now(timezone.utc).isoformat()

                # Update BOTH locale rows for this digest_type.
                # total_posts counts rows updated (EN + KO = 2 per digest_type). This differs
                # from _generate_digest's return semantics (which counts digests generated),
                # but is the honest metric here: we touched 2 rows.
                for slug in (
                    f"{batch_id.lower()}-{digest_type}-digest",
                    f"{batch_id.lower()}-{digest_type}-digest-ko",
                ):
                    try:
                        supabase.table("news_posts").update({
                            "quality_score": score_int,
                            "quality_flags": flags,
                            "content_analysis": content_analysis,
                            "analyzed_at": analyzed_at,
                        }).eq("slug", slug).execute()
                        total_posts += 1
                    except Exception as e:
                        all_errors.append(f"Failed to update {slug}: {e}")

            status = "failed" if all_errors else ("success" if total_posts > 0 else "failed")

            # Log summary stage (mirrors daily + non-quality rerun paths)
            t_summary = time.monotonic()
            await _log_stage(
                supabase, run_id, "summary", status, t_summary,
                input_summary=f"rerun from {from_stage}" + (f" ({category})" if category else ""),
                output_summary=f"{total_posts} rows rescored",
                usage=cumulative_usage,
                error_message="; ".join(all_errors) if all_errors else None,
            )

            supabase.table("pipeline_runs").update({
                "status": status,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "last_error": "; ".join(all_errors) if all_errors else None,
            }).eq("id", run_id).execute()

            return PipelineResult(
                batch_id=batch_id,
                status=status,
                posts_created=total_posts,
                errors=all_errors,
                usage=cumulative_usage,
            )

        # Load necessary checkpoints
        collect_data = _load_checkpoint(supabase, source_run_id, "collect")
        if not collect_data:
            raise ValueError("Checkpoint not found: collect")
        candidates = [NewsCandidate(**c) for c in collect_data.get("candidates", [])]
        raw_content_map = {c.url: c.raw_content for c in candidates if c.raw_content}
        handbook_slugs = _fetch_handbook_slugs(supabase)

        classification = ClassificationResult()

        # --- Load or rerun classify ---
        if from_stage == "classify":
            t0 = time.monotonic()
            classification, classify_usage, _ = await classify_candidates(candidates)
            cumulative_usage = merge_usage_metrics(cumulative_usage, classify_usage)
            _save_checkpoint(supabase, run_id, "classify", {
                "research_picks": [c.model_dump() for c in classification.research_picks],
                "business_picks": [c.model_dump() for c in classification.business_picks],
            })
            await _log_stage(supabase, run_id, "classify", "success", t0,
                             output_summary=f"research={len(classification.research_picks)}, business={len(classification.business_picks)}",
                             usage=classify_usage)
        else:
            classify_data = _load_checkpoint(supabase, source_run_id, "classify")
            if classify_data:
                classification.research_picks = [ClassifiedCandidate(**c) for c in classify_data.get("research_picks", [])]
                classification.business_picks = [ClassifiedCandidate(**c) for c in classify_data.get("business_picks", [])]

        # --- Load or rerun merge ---
        if from_stage in ("classify", "merge"):
            t0 = time.monotonic()
            classification, merge_usage = await merge_classified(classification, candidates)
            cumulative_usage = merge_usage_metrics(cumulative_usage, merge_usage)
            _save_checkpoint(supabase, run_id, "merge", {
                "research": [g.model_dump() for g in classification.research],
                "business": [g.model_dump() for g in classification.business],
            })
            await _log_stage(supabase, run_id, "merge", "success", t0,
                             output_summary=f"research={len(classification.research)}, business={len(classification.business)}",
                             usage=merge_usage)
        else:
            merge_data = _load_checkpoint(supabase, source_run_id, "merge")
            if merge_data:
                classification.research = [ClassifiedGroup(**g) for g in merge_data.get("research", [])]
                classification.business = [ClassifiedGroup(**g) for g in merge_data.get("business", [])]

        # --- Load or rerun community + rank + enrich ---
        if from_stage in ("classify", "merge", "community"):
            # Community
            t0 = time.monotonic()
            all_classified = classification.research + classification.business
            seen_urls: set[str] = set()
            community_lookup: list[tuple[str, str]] = []
            for group in all_classified:
                search_title = group.group_title
                for item in group.items:
                    if item.url not in seen_urls:
                        seen_urls.add(item.url)
                        community_lookup.append((search_title, item.url))
            community_map: dict[str, str] = {}
            _target_date = batch_id.replace("news-", "") if batch_id.startswith("news-") else batch_id
            if community_lookup:
                community_tasks = [collect_community_reactions(t, u, target_date=_target_date) for t, u in community_lookup]
                community_results = await asyncio.gather(*community_tasks, return_exceptions=True)
                for (_, url), result in zip(community_lookup, community_results):
                    if isinstance(result, str) and result.strip():
                        community_map[url] = result
            _save_checkpoint(supabase, run_id, "community", {"community_map": community_map})
            await _log_stage(supabase, run_id, "community", "success", t0,
                             output_summary=f"{len(community_map)} reactions")

            # Community Summarize
            t0 = time.monotonic()
            community_summary_map, cs_usage = await summarize_community(
                community_map, all_classified,
            )
            cumulative_usage = merge_usage_metrics(cumulative_usage, cs_usage)
            _save_checkpoint(supabase, run_id, "community_summarize", {
                "summaries": {url: ins.model_dump() for url, ins in community_summary_map.items()},
            })
            await _log_stage(supabase, run_id, "community_summarize", "success", t0,
                             output_summary=f"{len(community_summary_map)} insights",
                             usage=cs_usage)

            # Rank
            t0 = time.monotonic()
            r_ranked, r_usage = await rank_classified(classification.research, "research", community_map)
            b_ranked, b_usage = await rank_classified(classification.business, "business", community_map)
            classification.research = r_ranked
            classification.business = b_ranked
            rank_usage = merge_usage_metrics(r_usage, b_usage)
            cumulative_usage = merge_usage_metrics(cumulative_usage, rank_usage)
            _save_checkpoint(supabase, run_id, "rank", {
                "research": [g.model_dump() for g in classification.research],
                "business": [g.model_dump() for g in classification.business],
            })
            await _log_stage(supabase, run_id, "ranking", "success", t0, usage=rank_usage)

            # Enrich
            t0 = time.monotonic()
            all_ranked = classification.research + classification.business
            enriched_map = await enrich_sources(all_ranked, raw_content_map, target_date=batch_id)
            _save_checkpoint(supabase, run_id, "enrich", {
                "enriched_map": enriched_map,
                "raw_content_map": {k: v[:15000] for k, v in raw_content_map.items()},
            })
            await _log_stage(supabase, run_id, "enrich", "success", t0,
                             output_summary=f"{sum(len(s) for s in enriched_map.values())} sources")
        else:
            # Load from checkpoint (write-only rerun)
            community_data = _load_checkpoint(supabase, source_run_id, "community")
            community_map = community_data.get("community_map", {}) if community_data else {}

            cs_data = _load_checkpoint(supabase, source_run_id, "community_summarize")
            if cs_data and cs_data.get("summaries"):
                community_summary_map = {
                    url: CommunityInsight(**ins_data)
                    for url, ins_data in cs_data["summaries"].items()
                }
            else:
                # Fallback: run summarizer on loaded community_map
                all_classified = classification.research + classification.business
                community_summary_map, _ = await summarize_community(community_map, all_classified)

            rank_data = _load_checkpoint(supabase, source_run_id, "rank")
            if rank_data:
                classification.research = [ClassifiedGroup(**g) for g in rank_data.get("research", [])]
                classification.business = [ClassifiedGroup(**g) for g in rank_data.get("business", [])]

            enrich_data = _load_checkpoint(supabase, source_run_id, "enrich")
            enriched_map = enrich_data.get("enriched_map", {}) if enrich_data else {}
            if enrich_data and enrich_data.get("raw_content_map"):
                raw_content_map = enrich_data["raw_content_map"]

        # --- Always run write (digest generation) ---
        digest_tasks = []
        for digest_type, classified_items in [
            ("research", classification.research),
            ("business", classification.business),
        ]:
            if not classified_items:
                continue
            if category and digest_type != category:
                continue  # Skip if category filter is set
            digest_tasks.append(
                _generate_digest(
                    classified=classified_items,
                    digest_type=digest_type,
                    batch_id=batch_id,
                    handbook_slugs=handbook_slugs,
                    raw_content_map=raw_content_map,
                    community_summary_map=community_summary_map,
                    supabase=supabase,
                    run_id=run_id,
                    enriched_map=enriched_map,
                    auto_publish=False,
                )
            )

        digest_results = await asyncio.gather(*digest_tasks, return_exceptions=True)
        for result in digest_results:
            if isinstance(result, Exception):
                all_errors.append(f"Digest generation failed: {result}")
            else:
                posts, errors, usage = result
                total_posts += posts
                all_errors.extend(errors)
                cumulative_usage = merge_usage_metrics(cumulative_usage, usage)

        status = "failed" if all_errors else ("success" if total_posts > 0 else "failed")

        # Log summary (same as daily pipeline — cumulative usage for this rerun)
        t_summary = time.monotonic()
        await _log_stage(
            supabase, run_id, "summary", status, t_summary,
            input_summary=f"rerun from {from_stage}" + (f" ({category})" if category else ""),
            output_summary=f"{total_posts} posts created",
            usage=cumulative_usage,
            error_message="; ".join(all_errors) if all_errors else None,
        )

        supabase.table("pipeline_runs").update({
            "status": status,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "last_error": "; ".join(all_errors) if all_errors else None,
        }).eq("id", run_id).execute()

        return PipelineResult(
            batch_id=batch_id,
            status=status,
            posts_created=total_posts,
            errors=all_errors,
            usage=cumulative_usage,
        )

    except Exception as e:
        logger.error("Rerun pipeline failed: %s", e)
        try:
            supabase.table("pipeline_runs").update({
                "status": "failed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "last_error": str(e),
            }).eq("id", run_id).execute()
        except Exception:
            pass
        return PipelineResult(batch_id=batch_id, status="failed", message=str(e))


async def run_handbook_extraction(batch_id: str) -> PipelineResult:
    """Run handbook term extraction from existing news posts. Independent pipeline run.

    Reads news_posts for the given batch_id and extracts/generates handbook terms.
    Can be called independently to retry after failure without re-running news.
    """
    supabase = get_supabase()
    if not supabase:
        return PipelineResult(batch_id=batch_id, errors=["Supabase not configured"])

    # Fetch article content from existing news posts
    try:
        posts_result = (
            supabase.table("news_posts")
            .select("content_expert, title")
            .eq("pipeline_batch_id", batch_id)
            .eq("locale", "en")
            .execute()
        )
        article_texts = [
            p.get("content_expert", "") or p.get("title", "")
            for p in (posts_result.data or [])
            if p.get("content_expert") or p.get("title")
        ]
    except Exception as e:
        return PipelineResult(batch_id=batch_id, errors=[f"Failed to fetch posts: {e}"])

    if not article_texts:
        logger.info("No article content for handbook extraction (batch %s)", batch_id)
        return PipelineResult(batch_id=batch_id)

    # Create separate pipeline run with attempt numbering to preserve logs
    run_id = str(uuid.uuid4())
    run_key = f"handbook-extract-{batch_id}"
    all_errors: list[str] = []

    # Check for existing runs to determine attempt number
    try:
        existing = supabase.table("pipeline_runs").select("id").like("run_key", f"handbook-extract-{batch_id}%").execute()
        attempt = len(existing.data or []) + 1
        if attempt > 1:
            run_key = f"handbook-extract-{batch_id}-a{attempt}"
    except Exception:
        pass  # proceed with base run_key

    # P1-3: Distinguish duplicate vs other insert failures
    try:
        supabase.table("pipeline_runs").insert({
            "id": run_id,
            "run_key": run_key,
            "status": "running",
        }).execute()
    except Exception as e:
        err_msg = str(e).lower()
        if "duplicate" in err_msg or "already exists" in err_msg or "unique" in err_msg:
            logger.info("Handbook extraction run already exists for %s, skipping", batch_id)
            return PipelineResult(batch_id=batch_id, status="skipped", message=f"Duplicate handbook run: {batch_id}")
        logger.error("Handbook extraction run insert failed for %s: %s", batch_id, e)
        return PipelineResult(batch_id=batch_id, status="failed", errors=[f"Run insert failed: {e}"])

    try:
        terms_created, errors = await _extract_and_create_handbook_terms(
            article_texts, supabase, run_id,
        )
        all_errors.extend(errors)

        # P1-2: Only use success/failed (DB constraint doesn't allow "partial")
        status = "failed" if terms_created == 0 and errors else "success"
        try:
            supabase.table("pipeline_runs").update({
                "status": status,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "last_error": errors[0] if errors else None,
            }).eq("id", run_id).execute()
        except Exception as e:
            logger.warning("Failed to update handbook run: %s", e)

        logger.info(
            "Handbook extraction complete (batch %s): %d terms, %d errors",
            batch_id, terms_created, len(errors),
        )
        # P1-1: Return actual results from success path
        return PipelineResult(
            batch_id=batch_id, status=status,
            posts_created=terms_created, errors=all_errors,
        )
    except Exception as e:
        logger.error("Handbook extraction failed: %s", e)
        all_errors.append(str(e))
        try:
            supabase.table("pipeline_runs").update({
                "status": "failed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "last_error": str(e),
            }).eq("id", run_id).execute()
        except Exception:
            pass
        return PipelineResult(
            batch_id=batch_id, status="failed",
            posts_created=0, errors=all_errors,
        )


# ──────────────────────────────────────────────
# WEEKLY RECAP PIPELINE
# ──────────────────────────────────────────────

async def run_weekly_pipeline(
    week_id: str | None = None,
) -> PipelineResult:
    """Generate weekly recap from Mon-Fri daily digests.

    Flow: fetch EN+KO dailies -> LLM generates EN+KO simultaneously (like daily) -> save drafts.
    """
    from services.agents.prompts_news_pipeline import get_weekly_prompt

    if week_id is None:
        last_week = datetime.strptime(today_kst(), "%Y-%m-%d").date() - timedelta(days=7)
        week_id = _iso_week_id(last_week)

    supabase = get_supabase()
    if not supabase:
        return PipelineResult(batch_id=week_id, errors=["Supabase not configured"])

    run_key = f"weekly-{week_id}"
    try:
        _res = supabase.table("pipeline_runs").select("id, status").eq("run_key", run_key).limit(1).execute()
        existing = _res.data[0] if _res.data else None
        if existing:
            run_id = existing["id"]
            supabase.table("pipeline_logs").delete().eq("run_id", run_id).execute()
            supabase.table("pipeline_runs").update({
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "finished_at": None,
                "last_error": None,
            }).eq("id", run_id).execute()
            logger.info("Reusing existing weekly run %s (was %s)", run_key, existing["status"])
        else:
            run_id = str(uuid.uuid4())
            supabase.table("pipeline_runs").insert({
                "id": run_id, "run_key": run_key, "status": "running",
            }).execute()
    except Exception as e:
        logger.warning("Weekly run setup failed for %s: %s", week_id, e)
        return PipelineResult(batch_id=week_id, status="skipped", message=f"Setup error: {e}")

    all_errors: list[str] = []
    cumulative_usage: dict[str, Any] = {}
    total_posts = 0

    try:
        # Stage: fetch EN + KO digests
        t0 = time.monotonic()
        try:
            digests_en = await _fetch_week_digests(supabase, week_id, "en")
            digests_ko = await _fetch_week_digests(supabase, week_id, "ko")
        except Exception as e:
            await _log_stage(supabase, run_id, "weekly:fetch", "failed", t0,
                             error_message=str(e), post_type="weekly")
            raise
        await _log_stage(supabase, run_id, "weekly:fetch", "success", t0,
                         output_summary=f"en={len(digests_en)}, ko={len(digests_ko)} digests",
                         post_type="weekly")

        if not digests_en:
            all_errors.append(f"No EN daily digests for {week_id}")

        # Build URL → tier/kind map from daily source_cards
        url_meta: dict[str, dict] = {}
        for d in digests_en + digests_ko:
            for card in (d.get("source_cards") or []):
                url = card.get("url", "")
                if url and url not in url_meta:
                    url_meta[url] = {
                        "source_tier": card.get("source_tier", ""),
                        "source_kind": card.get("source_kind", ""),
                    }
        aggregate_urls = set(url_meta.keys())

        # Classify primary vs secondary for LLM reference
        primary_urls = [u for u, m in url_meta.items()
                        if (m.get("source_tier") or "").lower() == "primary"]
        secondary_urls = [u for u, m in url_meta.items()
                          if (m.get("source_tier") or "").lower() != "primary"]

        # Stage: fetch handbook terms
        t0 = time.monotonic()
        week_terms_en: list[dict] = []
        week_terms_ko: list[dict] = []
        try:
            week_terms_en = await _fetch_week_handbook_terms(supabase, week_id, "en")
            week_terms_ko = await _fetch_week_handbook_terms(supabase, week_id, "ko")
        except Exception as e:
            logger.warning("Weekly handbook terms fetch failed: %s", e)
        await _log_stage(supabase, run_id, "weekly:terms", "success", t0,
                         output_summary=f"en={len(week_terms_en)}, ko={len(week_terms_ko)} terms",
                         post_type="weekly")

        # Build SOURCE REFERENCE header for LLM
        source_ref_lines = []
        if primary_urls:
            source_ref_lines.append("PRIMARY: " + " | ".join(primary_urls[:30]))
        if secondary_urls:
            source_ref_lines.append("SECONDARY: " + " | ".join(secondary_urls[:30]))
        source_ref = ""
        if source_ref_lines:
            source_ref = "## SOURCE REFERENCE (for citation priority — cite PRIMARY URLs before SECONDARY)\n" + "\n".join(source_ref_lines) + "\n\n"

        # Build per-persona input (EN primary + KO reference)
        persona_inputs: dict[str, str] = {}
        for persona in ("expert", "learner"):
            content_key = f"content_{persona}"
            parts = []
            # EN digests (primary)
            for d in digests_en:
                content = d.get(content_key, "")
                if content:
                    parts.append(f"--- {d['post_type'].upper()} EN ({d.get('published_at', '')}) ---\n# {d['title']}\n\n{content}")
            # KO digests (reference)
            for d in digests_ko:
                content = d.get(content_key, "")
                if content:
                    parts.append(f"--- {d['post_type'].upper()} KO ({d.get('published_at', '')}) ---\n# {d['title']}\n\n{content}")
            persona_inputs[persona] = source_ref + "\n\n".join(parts)

        # Generate per persona: Call 1 (EN from digests) → Call 2 (KO from EN)
        from services.agents.prompts_news_pipeline import get_weekly_ko_prompt
        persona_results: dict[str, dict] = {}
        client = get_openai_client()
        model = settings.openai_model_main

        async def _gen_weekly_persona(persona: str) -> None:
            daily_text = persona_inputs.get(persona, "")
            if not daily_text:
                return

            # Call 1: EN generation from daily digests
            t_en = time.monotonic()
            system_prompt = get_weekly_prompt(persona)
            try:
                en_response = await asyncio.wait_for(
                    client.chat.completions.create(
                        **compat_create_kwargs(
                            model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": daily_text},
                            ],
                            response_format={"type": "json_object"},
                            temperature=0.5,
                            max_tokens=16000,
                        )
                    ),
                    timeout=240,
                )
                en_raw = en_response.choices[0].message.content or ""
                en_usage = extract_usage_metrics(en_response, model)
                cumulative_usage.update(merge_usage_metrics(cumulative_usage, en_usage))
                en_data = parse_ai_json(en_raw, f"weekly-{persona}-en")

                await _log_stage(
                    supabase, run_id, f"weekly:{persona}:en", "success", t_en,
                    output_summary=f"en={len(en_data.get('en', ''))}c",
                    usage=en_usage, post_type="weekly",
                )
            except Exception as e:
                logger.warning("Weekly %s EN failed: %s", persona, e)
                all_errors.append(f"weekly {persona} EN: {e}")
                await _log_stage(
                    supabase, run_id, f"weekly:{persona}:en", "failed", t_en,
                    error_message=str(e), post_type="weekly",
                )
                return

            en_content = en_data.get("en", "")
            if not en_content.strip():
                all_errors.append(f"weekly {persona} EN: empty content")
                return

            # Append the EN weekly_quiz JSON under a marker so the KO adapter can translate
            # it 1:1. Without this, the LLM only sees the markdown body and cannot produce
            # weekly_quiz_ko.
            import json as _json
            en_quiz = en_data.get("weekly_quiz") or []
            en_excerpt = (en_data.get("excerpt") or "").strip()
            en_focus = en_data.get("focus_items") or []

            ko_input_parts = [en_content]
            if en_quiz:
                ko_input_parts.append(
                    "---ENGLISH WEEKLY QUIZ (JSON, translate to weekly_quiz_ko)---\n"
                    + _json.dumps(en_quiz, ensure_ascii=False, indent=2)
                )
            if en_excerpt or en_focus:
                meta = {"excerpt": en_excerpt, "focus_items": en_focus}
                ko_input_parts.append(
                    "---ENGLISH META (JSON, translate to excerpt_ko + focus_items_ko)---\n"
                    + _json.dumps(meta, ensure_ascii=False, indent=2)
                )
            ko_input = "\n\n".join(ko_input_parts)

            # Call 2: KO adaptation from EN result
            t_ko = time.monotonic()
            ko_prompt = get_weekly_ko_prompt(persona)
            try:
                ko_response = await asyncio.wait_for(
                    client.chat.completions.create(
                        **compat_create_kwargs(
                            model,
                            messages=[
                                {"role": "system", "content": ko_prompt},
                                {"role": "user", "content": ko_input},
                            ],
                            response_format={"type": "json_object"},
                            temperature=0.5,
                            max_tokens=16000,
                        )
                    ),
                    timeout=180,
                )
                ko_raw = ko_response.choices[0].message.content or ""
                ko_usage = extract_usage_metrics(ko_response, model)
                cumulative_usage.update(merge_usage_metrics(cumulative_usage, ko_usage))
                ko_data = parse_ai_json(ko_raw, f"weekly-{persona}-ko")

                await _log_stage(
                    supabase, run_id, f"weekly:{persona}:ko", "success", t_ko,
                    output_summary=f"ko={len(ko_data.get('ko', ''))}c",
                    usage=ko_usage, post_type="weekly",
                )
            except Exception as e:
                logger.warning("Weekly %s KO failed: %s", persona, e)
                all_errors.append(f"weekly {persona} KO: {e}")
                ko_data = {}
                await _log_stage(
                    supabase, run_id, f"weekly:{persona}:ko", "failed", t_ko,
                    error_message=str(e), post_type="weekly",
                )

            # Merge EN + KO results
            persona_results[persona] = {**en_data, **ko_data}

        await asyncio.gather(
            _gen_weekly_persona("expert"),
            _gen_weekly_persona("learner"),
        )

        if not persona_results:
            all_errors.append("All weekly personas failed")
        else:
            expert_data = persona_results.get("expert", {})
            learner_data = persona_results.get("learner", {})

            headline_en = expert_data.get("headline") or f"AI Weekly — {week_id}"
            headline_learner_en = learner_data.get("headline") or headline_en
            headline_ko = expert_data.get("headline_ko") or headline_en
            headline_learner_ko = learner_data.get("headline_ko") or headline_ko

            # published_at = Sunday of the target week at 09:00 UTC
            iso_year, iso_week = week_id.split("-W")
            _monday = datetime.strptime(f"{iso_year}-W{int(iso_week)}-1", "%G-W%V-%u").date()
            _sunday = _monday + timedelta(days=6)
            published_at = f"{_sunday.isoformat()}T09:00:00Z"

            guide_items = {
                "week_numbers": expert_data.get("week_numbers") or learner_data.get("week_numbers", []),
                "week_tool": expert_data.get("week_tool") or learner_data.get("week_tool", {}),
            }

            # Clean + renumber citations (same URL → same number, sequential)
            en_expert = _clean_writer_output(expert_data.get("en", ""))
            ko_expert = _clean_writer_output(expert_data.get("ko", ""))
            en_learner = _clean_writer_output(learner_data.get("en", ""))
            ko_learner = _clean_writer_output(learner_data.get("ko", ""))

            # NP-QUALITY-03: HEAD-check aggregate URLs; dead ones stripped from
            # bodies by _renumber_citations via the tightened allowlist.
            if aggregate_urls:
                from services.pipeline_quality import _validate_urls_live
                live_agg, dead_drops = await _validate_urls_live(aggregate_urls)
                if dead_drops:
                    logger.warning(
                        "Weekly URL liveness dropped %d of %d URLs: %s",
                        len(dead_drops), len(aggregate_urls),
                        "; ".join(f"{d['url'][:60]} ({d['reason']})" for d in dead_drops[:5]),
                    )
                aggregate_urls = live_agg
            _allowed = aggregate_urls if aggregate_urls else None
            en_expert, en_expert_cards = _renumber_citations(en_expert, allowed_urls=_allowed)
            ko_expert, ko_expert_cards = _renumber_citations(ko_expert, allowed_urls=_allowed)
            en_learner, en_learner_cards = _renumber_citations(en_learner, allowed_urls=_allowed)
            ko_learner, ko_learner_cards = _renumber_citations(ko_learner, allowed_urls=_allowed)

            weekly_source_cards = {
                "en": _dedup_source_cards((en_expert_cards or []) + (en_learner_cards or [])),
                "ko": _dedup_source_cards((ko_expert_cards or []) + (ko_learner_cards or [])),
            }

            # Quality check
            from services.pipeline_quality import _check_weekly_quality
            quality_result = await _check_weekly_quality(
                content_expert_en=en_expert,
                content_learner_en=en_learner,
                content_expert_ko=ko_expert,
                content_learner_ko=ko_learner,
                source_urls=list(aggregate_urls) if aggregate_urls else [],
                supabase=supabase,
                run_id=run_id,
                cumulative_usage=cumulative_usage,
            )
            quality_score = quality_result.get("quality_score")
            quality_flags = quality_result.get("quality_flags")
            # _check_weekly_quality's content_analysis field is internal QC feedback
            # (issue list). The news_posts.content_analysis column is rendered by the
            # frontend as user-facing markdown (the 'Core Analysis' section), so the
            # QC dump must NOT be saved there. QC issues remain available in
            # pipeline_logs for admin review.
            auto_publish = quality_result.get("auto_publish_eligible", False)

            # Save EN + KO rows
            for locale in ("en", "ko"):
                slug = f"{week_id.lower()}-weekly-digest" if locale == "en" else f"{week_id.lower()}-weekly-digest-ko"
                title = headline_en if locale == "en" else headline_ko
                title_learner = headline_learner_en if locale == "en" else headline_learner_ko

                content_expert = en_expert if locale == "en" else ko_expert
                content_learner = en_learner if locale == "en" else ko_learner

                # Reading time
                text = content_expert or content_learner
                if locale == "ko":
                    char_count = len([c for c in text if c.strip() and c not in '.,!?;:()[]{}"\'-\u2014\u2026#*_~`|/>'])
                    reading_time = max(1, round(char_count / 500))
                else:
                    reading_time = max(1, round(len(text.split()) / 200))

                # Terms for this locale
                terms = week_terms_en if locale == "en" else week_terms_ko

                # Weekly quiz per locale: EN reads `weekly_quiz`, KO reads `weekly_quiz_ko`
                # (the LLM generates EN quiz in call 1 and translates to KO in call 2).
                quiz_key = "weekly_quiz" if locale == "en" else "weekly_quiz_ko"
                expert_quiz = _validate_and_shuffle_weekly_quiz(expert_data.get(quiz_key))
                learner_quiz = _validate_and_shuffle_weekly_quiz(learner_data.get(quiz_key))

                # Excerpt + focus_items per locale
                excerpt_key = "excerpt" if locale == "en" else "excerpt_ko"
                focus_key = "focus_items" if locale == "en" else "focus_items_ko"

                excerpt = (expert_data.get(excerpt_key) or learner_data.get(excerpt_key) or "").strip()
                excerpt_learner = (learner_data.get(excerpt_key) or "").strip()

                focus_raw = expert_data.get(focus_key) or learner_data.get(focus_key) or []
                focus_items = _validate_focus_items(focus_raw)

                # Defend against LLM runaway length in excerpt
                if len(excerpt) > 1000:
                    excerpt = excerpt[:1000].rstrip() + '\u2026'

                locale_guide = {
                    **guide_items,
                    "week_terms": [
                        {
                            "slug": t["slug"],
                            "term": t.get("korean_name" if locale == "ko" else "term") or t.get("term", ""),
                            "definition": t.get(f"definition_{locale}", ""),
                        }
                        for t in terms[:2]
                    ],
                    "weekly_quiz_expert": expert_quiz,
                    "weekly_quiz_learner": learner_quiz,
                    "excerpt_learner": excerpt_learner,
                }

                locale_cards = weekly_source_cards.get(locale, [])
                row = {
                    "title": title,
                    "title_learner": title_learner,
                    "slug": slug,
                    "locale": locale,
                    "category": "ai-news",
                    "post_type": "weekly",
                    "status": "published" if (auto_publish and settings.weekly_auto_publish) else "draft",
                    "content_expert": content_expert,
                    "content_learner": content_learner,
                    "pipeline_batch_id": week_id,
                    "published_at": published_at,
                    "reading_time_min": reading_time,
                    "guide_items": locale_guide,
                    "source_urls": [c["url"] for c in locale_cards],
                    "source_cards": locale_cards,
                    "quality_score": quality_score,
                    "quality_flags": quality_flags,
                    "content_analysis": None,
                    "fact_pack": {},
                    "excerpt": excerpt or None,
                    "focus_items": focus_items,
                }

                t_save = time.monotonic()
                try:
                    existing_post = supabase.table("news_posts").select("id").eq("slug", slug).eq("locale", locale).limit(1).execute()
                    if existing_post.data:
                        supabase.table("news_posts").update(row).eq("id", existing_post.data[0]["id"]).execute()
                    else:
                        supabase.table("news_posts").insert(row).execute()
                    total_posts += 1
                    await _log_stage(supabase, run_id, f"weekly:save:{locale}", "success", t_save,
                                     output_summary=f"saved {slug}", post_type="weekly", locale=locale)
                except Exception as e:
                    all_errors.append(f"Save weekly {locale}: {e}")
                    await _log_stage(supabase, run_id, f"weekly:save:{locale}", "failed", t_save,
                                     error_message=str(e), post_type="weekly", locale=locale)

        # Buttondown email (disabled by default)
        if settings.weekly_email_enabled and total_posts > 0:
            try:
                await _send_weekly_email(supabase, week_id)
            except Exception as e:
                logger.warning("Weekly email failed: %s", e)
                all_errors.append(f"Email: {e}")

        status = "success" if total_posts > 0 and not all_errors else "partial" if total_posts > 0 else "failed"
        supabase.table("pipeline_runs").update({
            "status": status,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "last_error": "; ".join(all_errors) if all_errors else None,
        }).eq("id", run_id).execute()

        return PipelineResult(
            batch_id=week_id, status=status,
            total_posts=total_posts, errors=all_errors, usage=cumulative_usage,
        )

    except Exception as e:
        logger.error("Weekly pipeline failed: %s", e, exc_info=True)
        try:
            supabase.table("pipeline_runs").update({
                "status": "failed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "last_error": str(e)[:500],
            }).eq("id", run_id).execute()
        except Exception:
            pass
        return PipelineResult(batch_id=week_id, status="failed", errors=[str(e)])


# -----------------------------------------------------------------------------
# Backward-compat re-exports  (Phase 1 refactoring 2026-04-15)
#
# These imports MUST stay at the bottom of the file to avoid circular imports
# (pipeline_digest.py / pipeline_quality.py import helpers from pipeline.py).
#
# Two categories:
#   (a) Used by orchestrator code above  – called at runtime by
#       run_daily_pipeline / rerun_pipeline_stage / run_weekly_pipeline.
#   (b) Re-export only  – not called here, but external callers
#       (routers/cron.py, tests/*) still import them from services.pipeline.
# -----------------------------------------------------------------------------

# --- pipeline_persistence: (a) used + (b) re-export -------------------------
from services.pipeline_persistence import (  # noqa: E402, F401
    # (a) used by run_weekly_pipeline
    _fetch_week_digests,
    _fetch_week_handbook_terms,
    _iso_week_id,
    _send_weekly_email,
    # (b) re-export only
    _notify_auto_publish,
    _send_draft_alert,
    promote_drafts,
)

# --- pipeline_digest: (a) used + (b) re-export ------------------------------
from services.pipeline_digest import (  # noqa: E402, F401
    # (a) used by run_daily_pipeline / rerun_pipeline_stage / run_weekly_pipeline
    _clean_writer_output,
    _generate_digest,
    # (b) re-export only
    _extract_digest_items,
    _fix_bold_spacing,
    _map_digest_items_to_group_indexes,
    _strip_empty_sections,
)

# --- pipeline_quality: (b) re-export only ------------------------------------
from services.pipeline_quality import (  # noqa: E402, F401
    _apply_issue_penalties_and_caps,
    _body_paragraphs_for_quality,
    _build_body_quality_payload,
    _build_frontload_quality_payload,
    _check_digest_quality,
    _check_structural_penalties,
    _compute_locale_score,
    _compute_structure_score,
    _compute_traceability_score,
    _extract_structured_issues,
    _find_digest_blockers,
    _normalize_quality_issue,
    _normalize_scope,
    validate_citation_urls,
)

"""AI News Pipeline v3 orchestrator."""
import asyncio
import logging
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
from services.agents.client import build_completion_kwargs, compat_create_kwargs, extract_usage_metrics, get_openai_client, merge_usage_metrics, parse_ai_json
from services.agents.prompts_news_pipeline import get_digest_prompt
from services.agents.ranking import classify_candidates, merge_classified, rank_classified, summarize_community
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
    valid_terms: list[tuple[str, str, str, list[str]]] = []  # (term_name, korean_name, slug, categories)
    queued_terms: list[tuple[str, str, str, list[str]]] = []  # (term_name, korean_name, slug, categories)
    for term_info in extracted:
        term_name = term_info.get("term", "").strip()
        korean_name = term_info.get("korean_name", "").strip()
        if not term_name:
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
        if confidence == "low":
            queued_terms.append((term_name, korean_name, slug, all_cats))
            logger.info("Queuing low-confidence term '%s' for manual review", term_name)
        else:
            valid_terms.append((term_name, korean_name, slug, all_cats))

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
    deduped_valid: list[tuple[str, str, str, list[str]]] = []
    for term_name, korean_name, slug, cats in valid_terms:
        is_dup = False
        for existing_name, _, _, _ in deduped_valid:
            if _is_semantic_dup(term_name, existing_name):
                logger.info("Skipping '%s' — semantic duplicate of '%s'", term_name, existing_name)
                is_dup = True
                break
        if not is_dup:
            deduped_valid.append((term_name, korean_name, slug, cats))
    valid_terms = deduped_valid

    # LLM gate: verify candidates against existing handbook terms before expensive generation
    if valid_terms:
        try:
            existing = supabase.table("handbook_terms").select("term").neq("status", "archived").execute()
            existing_names = [r["term"] for r in (existing.data or [])]
            # Build candidate dicts for gate
            gate_candidates = [{"term": tn, "korean_name": kn} for tn, kn, _sl, _cats in valid_terms]
            accepted = await gate_candidate_terms(gate_candidates, existing_names)
            accepted_names = {c["term"] for c in accepted}
            before_count = len(valid_terms)
            valid_terms = [(tn, kn, sl, cats) for tn, kn, sl, cats in valid_terms if tn in accepted_names]
            rejected_count = before_count - len(valid_terms)
            if rejected_count:
                logger.info("LLM gate rejected %d/%d candidates", rejected_count, before_count)
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

            try:
                row = {
                    "term": term_name,
                    "slug": slug,
                    "korean_name": content_data.get("korean_name", korean_name),
                    "term_full": content_data.get("term_full", ""),
                    "korean_full": content_data.get("korean_full", ""),
                    "categories": content_data.get("categories", []),
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
            *[_create_single_term(tn, kn, sl, cats) for tn, kn, sl, cats in valid_terms],
        )
        for created, term_errors in term_results:
            terms_created += created
            errors.extend(term_errors)

    # Save low-confidence terms as queued (title only, no LLM generation)
    queued_count = 0
    for term_name, korean_name, slug, cats in queued_terms:
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


async def _check_digest_quality(
    personas: dict[str, PersonaOutput],
    digest_type: str,
    classified: list,
    community_summary_map: dict,
    supabase,
    run_id: str,
    cumulative_usage: dict[str, Any],
) -> int:
    """Score quality of generated digest. Expert + Learner evaluated separately.

    Returns combined score 0-100 (average of expert and learner scores).
    """
    t0 = time.monotonic()
    from services.agents.prompts_news_pipeline import (
        QUALITY_CHECK_RESEARCH_EXPERT, QUALITY_CHECK_RESEARCH_LEARNER,
        QUALITY_CHECK_BUSINESS_EXPERT, QUALITY_CHECK_BUSINESS_LEARNER,
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

    async def _score(prompt: str, content: str, label: str) -> tuple[int, dict, dict]:
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
                if not data or not data.get("score"):
                    logger.warning("Quality check %s attempt %d: no score in response", label, attempt + 1)
                    continue
                usage = extract_usage_metrics(resp, quality_model)
                return int(data.get("score", 0)), data, usage
            except Exception as e:
                logger.warning("Quality check %s attempt %d failed: %s", label, attempt + 1, e)
        logger.error("Quality check %s failed after %d attempts", label, max_retries)
        return 0, {}, {}

    # Run expert + learner quality checks in parallel
    tasks = [_score(expert_prompt, expert.en, f"Quality-{digest_type}-expert")]
    if learner and learner.en:
        tasks.append(_score(learner_prompt, learner.en, f"Quality-{digest_type}-learner"))

    results = await asyncio.gather(*tasks)

    expert_score, expert_breakdown, expert_usage = results[0]
    learner_score, learner_breakdown, learner_usage = (
        results[1] if len(results) > 1 else (0, {}, {})
    )

    if learner and learner.en:
        combined_score = (expert_score + learner_score) // 2
    else:
        combined_score = expert_score

    # Code-based structural penalties
    structural_penalty, structural_warnings = _check_structural_penalties(
        expert, learner, community_summary_map, classified,
    )
    if structural_penalty > 0:
        logger.info("Structural penalties for %s: -%d (%s)", digest_type, structural_penalty, "; ".join(structural_warnings))
    final_score = max(0, combined_score - structural_penalty)

    merged_quality_usage = merge_usage_metrics(expert_usage, learner_usage) if learner_usage else expert_usage

    await _log_stage(
        supabase, run_id, f"quality:{digest_type}", "success", t0,
        output_summary=f"score={final_score}/100 (expert={expert_score}, learner={learner_score}, penalty=-{structural_penalty})",
        usage=merged_quality_usage,
        post_type=digest_type,
        debug_meta={
            "score": final_score,
            "quality_score": final_score,
            "expert_score": expert_score,
            "learner_score": learner_score,
            "structural_penalty": structural_penalty,
            "structural_warnings": structural_warnings,
            "expert_breakdown": {k: v for k, v in expert_breakdown.items() if k != "score"},
            "learner_breakdown": {k: v for k, v in learner_breakdown.items() if k != "score"},
            "news_count": len(classified),
        },
    )

    logger.info(
        "Quality check %s: final=%d/100 (llm=%d, penalty=-%d)",
        digest_type, final_score, combined_score, structural_penalty,
    )
    return final_score


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

    # Check 7: One-Line Summary hard limit (-3 each, max -6)
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
        if output.ko:
            ko_line = _extract_one_liner(output.ko, "한 줄 요약")
            ko_len = len(_re.sub(r"\s+", "", ko_line))
            if ko_len > 60:
                penalty += 3
                warnings.append(
                    f"한 줄 요약 too long ({ko_len} chars > 60) in {persona_name} ko"
                )
        if output.en:
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


async def _send_draft_alert(batch_id: str, digest_type: str, quality_score: int | None) -> None:
    """Send email alert when a digest is saved as draft (below auto-publish threshold)."""
    if not settings.resend_api_key or not settings.admin_email:
        logger.info("Draft alert skipped — resend_api_key or admin_email not configured")
        return
    try:
        import httpx
        await httpx.AsyncClient().post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={
                "from": "0to1log <noreply@0to1log.com>",
                "to": [settings.admin_email],
                "subject": f"[0to1log] Draft alert: {batch_id} {digest_type} (score: {quality_score})",
                "text": (
                    f"{batch_id} {digest_type} scored {quality_score}/100 "
                    f"(threshold: {settings.auto_publish_threshold}).\n\n"
                    f"Saved as draft — manual review required.\n\n"
                    f"Admin: https://0to1log.com/admin/news"
                ),
            },
            timeout=10,
        )
        logger.info("Draft alert email sent for %s %s (score=%s)", batch_id, digest_type, quality_score)
    except Exception as e:
        logger.warning("Failed to send draft alert email: %s", e)


async def _notify_auto_publish(slugs: list[str]) -> None:
    """Notify frontend to fire webhooks + warm CDN for auto-published posts."""
    frontend_url = "https://0to1log.com"
    if not settings.cron_secret:
        logger.warning("cron_secret not set, skipping auto-publish notification")
        return
    for slug in slugs:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{frontend_url}/api/internal/notify-publish",
                    headers={"x-cron-secret": settings.cron_secret},
                    json={"slug": slug},
                    timeout=10,
                )
            logger.info("Auto-publish notification sent for %s", slug)
        except Exception as e:
            logger.warning("Failed to notify auto-publish for %s: %s", slug, e)


async def promote_drafts(batch_id: str | None = None) -> dict[str, Any]:
    """Promote eligible drafts (score >= threshold) from today's batch to published.

    Only promotes drafts with fact_pack.auto_publish_eligible=true (cron-triggered).
    Sends email alert for drafts below threshold. Fires webhooks for promoted posts.
    """
    if batch_id is None:
        batch_id = today_kst()

    supabase = get_supabase()
    if not supabase:
        logger.error("promote_drafts: Supabase unavailable")
        return {"promoted": 0, "kept_draft": 0, "errors": ["supabase unavailable"]}

    # Fetch all drafts for this batch
    result = (
        supabase.table("news_posts")
        .select("id,slug,quality_score,post_type,fact_pack,title")
        .eq("pipeline_batch_id", batch_id)
        .eq("status", "draft")
        .in_("post_type", ["research", "business"])
        .execute()
    )
    drafts = result.data or []
    logger.info("promote_drafts: %d drafts found for batch %s", len(drafts), batch_id)

    if not drafts:
        logger.warning("promote_drafts: no drafts found for batch %s — pipeline may have failed", batch_id)
        return {"promoted": 0, "kept_draft": 0, "batch_id": batch_id, "errors": ["no drafts found"]}

    threshold = settings.auto_publish_threshold
    promoted_slugs: list[str] = []
    kept_drafts: list[dict] = []
    errors: list[str] = []

    for draft in drafts:
        fp = draft.get("fact_pack") or {}
        eligible = fp.get("auto_publish_eligible", False)
        score = draft.get("quality_score")

        if not eligible:
            logger.info("Skipping %s — not eligible (manual trigger)", draft["slug"])
            continue

        if score is None or score < threshold:
            logger.info("Keeping draft %s — score %s < threshold %d", draft["slug"], score, threshold)
            kept_drafts.append(draft)
            continue

        # Promote to published
        try:
            supabase.table("news_posts").update({
                "status": "published",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", draft["id"]).execute()
            promoted_slugs.append(draft["slug"])
            logger.info("Promoted %s (score=%d) to published", draft["slug"], score)
        except Exception as e:
            error_msg = f"Failed to promote {draft['slug']}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    # Fire webhooks + warm CDN for promoted posts
    if promoted_slugs:
        await _notify_auto_publish(promoted_slugs)

    # Send draft alert emails (one per distinct post_type that was kept)
    alerted_types: set[str] = set()
    for d in kept_drafts:
        ptype = d.get("post_type") or "unknown"
        if ptype not in alerted_types:
            await _send_draft_alert(batch_id, ptype, d.get("quality_score"))
            alerted_types.add(ptype)

    return {
        "promoted": len(promoted_slugs),
        "kept_draft": len(kept_drafts),
        "promoted_slugs": promoted_slugs,
        "batch_id": batch_id,
        "errors": errors,
    }


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

    # Quality check — score the generated digest
    quality_score = await _check_digest_quality(
        personas, digest_type, classified, community_summary_map,
        supabase, run_id, cumulative_usage,
    )

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

        # Code-level dedup safety net: even if the LLM ignored the ALREADY COVERED
        # block, drop candidates whose entity tokens (company + product) overlap
        # heavily with recent headlines. This is a deterministic guard.
        dedup_dropped: list[str] = []
        if recent_headlines:
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
    from models.news_pipeline import ClassifiedCandidate, ClassificationResult, CommunityInsight, NewsCandidate

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

def _iso_week_id(d=None) -> str:
    """Return ISO week string like '2026-W13'."""
    if d is None:
        d = datetime.strptime(today_kst(), "%Y-%m-%d").date()
    iso_year, iso_week, _ = d.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


async def _fetch_week_digests(supabase, week_id: str, locale: str) -> list[dict]:
    """Fetch daily digests for the given ISO week and locale."""
    iso_year, iso_week = week_id.split("-W")
    monday = datetime.strptime(f"{iso_year}-W{int(iso_week)}-1", "%G-W%V-%u").date()
    sunday = monday + timedelta(days=6)

    result = (
        supabase.table("news_posts")
        .select("slug, title, post_type, content_expert, content_learner, published_at, guide_items")
        .eq("locale", locale)
        .eq("category", "ai-news")
        .in_("post_type", ["research", "business"])
        .eq("status", "published")
        .gte("published_at", monday.isoformat())
        .lte("published_at", sunday.isoformat() + "T23:59:59")
        .order("published_at", desc=False)
        .execute()
    )
    return result.data or []


async def _fetch_week_handbook_terms(supabase, week_id: str, locale: str) -> list[dict]:
    """Fetch handbook terms created/published this week for bottom card."""
    iso_year, iso_week = week_id.split("-W")
    monday = datetime.strptime(f"{iso_year}-W{int(iso_week)}-1", "%G-W%V-%u").date()
    sunday = monday + timedelta(days=6)

    result = (
        supabase.table("handbook_terms")
        .select("slug, term, korean_name, definition_en, definition_ko")
        .eq("status", "published")
        .gte("published_at", monday.isoformat())
        .lte("published_at", sunday.isoformat() + "T23:59:59")
        .limit(3)
        .execute()
    )
    return result.data or []


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
            persona_inputs[persona] = "\n\n".join(parts)

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
                                {"role": "user", "content": en_content},
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

            headline_en = expert_data.get("headline") or learner_data.get("headline") or f"AI Weekly — {week_id}"
            headline_ko = expert_data.get("headline_ko") or learner_data.get("headline_ko") or headline_en

            # published_at = Sunday of the target week at 09:00 UTC
            iso_year, iso_week = week_id.split("-W")
            _monday = datetime.strptime(f"{iso_year}-W{int(iso_week)}-1", "%G-W%V-%u").date()
            _sunday = _monday + timedelta(days=6)
            published_at = f"{_sunday.isoformat()}T09:00:00Z"

            guide_items = {
                "week_numbers": expert_data.get("week_numbers") or learner_data.get("week_numbers", []),
                "week_tool": expert_data.get("week_tool") or learner_data.get("week_tool", {}),
            }

            # Save EN + KO rows
            for locale in ("en", "ko"):
                slug = f"{week_id.lower()}-weekly-digest" if locale == "en" else f"{week_id.lower()}-weekly-digest-ko"
                title = headline_en if locale == "en" else headline_ko

                en_expert = _clean_writer_output(expert_data.get("en", ""))
                ko_expert = _clean_writer_output(expert_data.get("ko", ""))
                en_learner = _clean_writer_output(learner_data.get("en", ""))
                ko_learner = _clean_writer_output(learner_data.get("ko", ""))

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
                }

                row = {
                    "title": title,
                    "slug": slug,
                    "locale": locale,
                    "category": "ai-news",
                    "post_type": "weekly",
                    "status": "draft",
                    "content_expert": content_expert,
                    "content_learner": content_learner,
                    "pipeline_batch_id": week_id,
                    "published_at": published_at,
                    "reading_time_min": reading_time,
                    "guide_items": locale_guide,
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


async def _send_weekly_email(supabase, week_id: str) -> None:
    """Send weekly recap via Buttondown API (draft only — Amy sends manually)."""
    import httpx

    if not settings.buttondown_api_key:
        logger.info("Buttondown API key not set, skipping email")
        return

    slug = f"{week_id.lower()}-weekly-digest"
    result = (
        supabase.table("news_posts")
        .select("title, content_expert")
        .eq("slug", slug)
        .eq("locale", "en")
        .single()
        .execute()
    )

    if not result.data:
        logger.warning("No weekly post found for email: %s", slug)
        return

    async with httpx.AsyncClient() as http:
        resp = await http.post(
            "https://api.buttondown.com/v1/emails",
            headers={"Authorization": f"Token {settings.buttondown_api_key}"},
            json={
                "subject": result.data["title"],
                "body": result.data["content_expert"],
                "status": "draft",
            },
        )
        resp.raise_for_status()
        logger.info("Weekly email draft created in Buttondown for %s", week_id)

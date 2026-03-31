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
    ClassifiedGroup,
    PersonaOutput,
    PipelineResult,
)
from services.agents.advisor import (
    extract_terms_from_content,
    generate_term_content,
)
from services.agents.client import build_completion_kwargs, extract_usage_metrics, get_openai_client, merge_usage_metrics, parse_ai_json
from services.agents.prompts_news_pipeline import get_digest_prompt
from services.agents.ranking import classify_candidates, merge_classified, rank_classified
from services.news_collection import collect_community_reactions, collect_news, enrich_sources

logger = logging.getLogger(__name__)


def _fill_source_titles(
    code_cards: list[dict], llm_sources: list[dict],
) -> list[dict]:
    """Merge LLM-generated titles into code-extracted source_cards by URL matching."""
    if not code_cards:
        return code_cards
    url_to_title: dict[str, str] = {}
    for src in llm_sources:
        url = src.get("url", "")
        title = src.get("title", "")
        if url and title:
            url_to_title[url] = title
    return [
        {**card, "title": url_to_title.get(card["url"], card.get("title", ""))}
        for card in code_cards
    ]


def _renumber_citations(content: str) -> tuple[str, list[dict]]:
    """Renumber all [N](URL) citations sequentially by URL first-appearance order.

    Same URL always gets the same number. Returns (renumbered_content, source_cards).
    source_cards: [{id: 1, url: "...", title: ""}, ...] in order of appearance.
    """
    if not content:
        return content, []

    citation_re = re.compile(r'\[(\d+)\]\(([^)]+)\)')
    url_to_num: dict[str, int] = {}
    source_cards: list[dict] = []

    def _assign(url: str) -> int:
        if url not in url_to_num:
            num = len(url_to_num) + 1
            url_to_num[url] = num
            source_cards.append({"id": num, "url": url, "title": ""})
        return url_to_num[url]

    def _replace(match: re.Match) -> str:
        url = match.group(2)
        new_num = _assign(url)
        return f"[{new_num}]({url})"

    renumbered = citation_re.sub(_replace, content)
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

    # Combine article texts for extraction
    combined = "\n\n---\n\n".join(article_texts)
    if not combined.strip():
        return 0, []

    # Step 1: Extract terms
    t0 = time.monotonic()
    try:
        extracted, extract_usage = await extract_terms_from_content(combined)
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
        output_summary=f"{len(extracted)} terms extracted",
        usage=extract_usage,
        debug_meta={
            "terms": [t.get("term", "") for t in extracted],
        },
    )

    if not extracted:
        return 0, []

    # Step 2: Filter, dedup, and generate content for new terms (2 at a time)
    VALID_CATEGORIES = {
        "ai-ml", "db-data", "backend", "frontend-ux", "network",
        "security", "os-core", "devops", "performance", "web3",
        "ai-business",
    }

    # Pre-filter terms before generation
    valid_terms: list[tuple[str, str, str]] = []  # (term_name, korean_name, slug)
    queued_terms: list[tuple[str, str, str, str]] = []  # (term_name, korean_name, slug, category)
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
        category = term_info.get("category", "")
        if category not in VALID_CATEGORIES:
            logger.info("Skipping '%s' — invalid category '%s'", term_name, category)
            continue
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
        except Exception as e:
            logger.warning("Duplicate check failed for '%s': %s", term_name, e)
            continue

        confidence = term_info.get("confidence", "high")
        if confidence == "low":
            queued_terms.append((term_name, korean_name, slug, category))
            logger.info("Queuing low-confidence term '%s' for manual review", term_name)
        else:
            valid_terms.append((term_name, korean_name, slug))

    # Generate terms concurrently (max 2 at a time)
    sem = asyncio.Semaphore(2)
    pipeline_start = time.monotonic()
    PIPELINE_TIMEOUT_SEC = 30 * 60  # 30 minutes max for entire handbook pipeline

    TERM_TIMEOUT_SEC = 10 * 60  # 10 minutes max per single term generation

    async def _create_single_term(term_name: str, korean_name: str, slug: str) -> tuple[int, list[str]]:
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
            term_status = "queued" if any("quality score" in w.lower() for w in warnings) else "draft"

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

                logger.info("Created handbook draft: %s (%s)", term_name, slug)
                await _log_stage(
                    supabase, run_id, "handbook.auto_generate", "success", t_gen,
                    output_summary=f"term={term_name}, slug={slug}",
                    debug_meta={"term": term_name, "slug": slug, "source": "pipeline"},
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
            *[_create_single_term(tn, kn, sl) for tn, kn, sl in valid_terms],
        )
        for created, term_errors in term_results:
            terms_created += created
            errors.extend(term_errors)

    # Save low-confidence terms as queued (title only, no LLM generation)
    queued_count = 0
    for term_name, korean_name, slug, category in queued_terms:
        try:
            supabase.table("handbook_terms").insert({
                "term": term_name,
                "slug": slug,
                "korean_name": korean_name,
                "categories": [category],
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
    quality_model = settings.openai_model_light  # gpt-4.1-mini — cheaper and more reliable for scoring

    async def _score(prompt: str, content: str, label: str) -> tuple[int, dict, dict]:
        try:
            resp = await client.chat.completions.create(
                **build_completion_kwargs(
                    model=quality_model,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": content[:12000]},
                    ],
                    max_tokens=500,
                    temperature=0,
                    response_format={"type": "json_object"},
                )
            )
            data = parse_ai_json(resp.choices[0].message.content, label)
            usage = extract_usage_metrics(resp, quality_model)
            return int(data.get("score", 0)), data, usage
        except Exception as e:
            logger.warning("Quality check %s failed: %s", label, e)
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

    merged_quality_usage = merge_usage_metrics(expert_usage, learner_usage) if learner_usage else expert_usage

    await _log_stage(
        supabase, run_id, f"quality:{digest_type}", "success", t0,
        output_summary=f"score={combined_score}/100 (expert={expert_score}, learner={learner_score})",
        usage=merged_quality_usage,
        post_type=digest_type,
        debug_meta={
            "score": combined_score,
            "quality_score": combined_score,
            "expert_score": expert_score,
            "learner_score": learner_score,
            "expert_breakdown": {k: v for k, v in expert_breakdown.items() if k != "score"},
            "learner_breakdown": {k: v for k, v in learner_breakdown.items() if k != "score"},
            "news_count": len(classified),
        },
    )

    logger.info(
        "Quality check %s: combined=%d/100 (expert=%d, learner=%d)",
        digest_type, combined_score, expert_score, learner_score,
    )
    return combined_score


async def _generate_digest(
    classified: list[ClassifiedGroup],
    digest_type: str,
    batch_id: str,
    handbook_slugs: list[str],
    raw_content_map: dict[str, str],
    community_map: dict[str, str],
    supabase,
    run_id: str,
    enriched_map: dict[str, list[dict]] | None = None,
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

    # Build user prompt from classified groups
    _enriched = enriched_map or {}
    news_items = []
    for group in classified:
        # Multi-source: use enriched sources (from merge or Exa), else raw_content
        sources = _enriched.get(group.primary_url)
        if sources:
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
                source_blocks.append(f"Source {i}: {src['url']}\n{content}")
            body_block = "\n\n".join(source_blocks)
        else:
            # Fallback: assemble from raw_content_map for each item in group
            source_blocks = []
            for i, item in enumerate(group.items, 1):
                content = raw_content_map.get(item.url, "")
                if len(content.strip()) < 40:
                    continue
                source_blocks.append(f"Source {i}: {item.url}\n{content}")
            if not source_blocks:
                logger.info("Skipping group '%s' — no substantive content", group.group_title[:60])
                continue
            body_block = "\n\n".join(source_blocks)

        # Collect community from any URL in the group
        community = ""
        for item in group.items:
            community = community_map.get(item.url, "")
            if community:
                break
        community_block = f"\n\nCommunity Reactions (Reddit/HN):\n{community[:1000]}" if community else ""
        role_tag = "[LEAD]" if group.reason.startswith("[LEAD]") else "[SUPPORTING]"
        news_items.append(
            f"### {role_tag} [{group.subcategory}] {group.group_title}\n\n"
            f"{body_block}{community_block}"
        )
    user_prompt = "\n\n---\n\n".join(news_items)

    # Generate personas
    client = get_openai_client()
    model = settings.openai_model_main
    personas: dict[str, PersonaOutput] = {}
    digest_headline = ""
    digest_headline_ko = ""
    digest_excerpt = ""
    digest_excerpt_ko = ""
    persona_sources: dict[str, list[dict]] = {}  # {"expert": [...], "learner": [...]}
    digest_tags: list[str] = []
    digest_focus_items: list[str] = []
    digest_focus_items_ko: list[str] = []
    persona_quizzes: dict[str, dict] = {}  # {"expert": {"en": {...}, "ko": {...}}, "learner": {...}}

    MAX_DIGEST_RETRIES = 1  # 1 retry = 2 total attempts

    for persona_name in ("expert", "learner"):
        t_p = time.monotonic()
        system_prompt = get_digest_prompt(digest_type, persona_name, handbook_slugs)

        for attempt in range(MAX_DIGEST_RETRIES + 1):
            try:
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.4,
                        max_tokens=16000,
                    ),
                    timeout=180,  # 3 minutes max per digest call
                )
                data = parse_ai_json(
                    response.choices[0].message.content,
                    f"Digest-{digest_type}-{persona_name}",
                )
                persona_output = PersonaOutput(
                    en=data.get("en", ""),
                    ko=data.get("ko", ""),
                )

                # Capture metadata from first persona (expert)
                def _has_ko(s: str) -> bool:
                    return any('\uAC00' <= c <= '\uD7AF' for c in s)
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
                                model=model,
                                messages=[
                                    {"role": "system", "content": ko_system},
                                    {"role": "user", "content": user_prompt},
                                ],
                                response_format={"type": "json_object"},
                                temperature=0.4,
                                max_tokens=8000,
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
                                model=model,
                                messages=[
                                    {"role": "system", "content": en_system},
                                    {"role": "user", "content": user_prompt},
                                ],
                                response_format={"type": "json_object"},
                                temperature=0.4,
                                max_tokens=8000,
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

    # Quality check — score the generated digest
    quality_score = await _check_digest_quality(
        personas, digest_type, classified, supabase, run_id, cumulative_usage,
    )

    # Save EN + KO rows
    missing = [p for p in ("expert", "learner") if p not in personas]
    if missing:
        logger.warning("Missing personas for %s digest: %s", digest_type, missing)

    t_save = time.monotonic()
    translation_group_id = str(uuid.uuid4())
    slug_base = f"{batch_id}-{digest_type}-digest"

    source_urls = [url for group in classified for url in group.urls]
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
        # LLM may reset [1] per section — this forces global sequential numbering
        expert_content, expert_source_cards = _renumber_citations(expert_content)
        learner_content, learner_source_cards = _renumber_citations(learner_content)


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
            "source_urls": source_urls,
            "source_cards": _fill_source_titles(
                expert_source_cards or learner_source_cards,
                persona_sources.get("expert") or persona_sources.get("learner") or [],
            ),
            "fact_pack": {**digest_meta, "quality_score": quality_score},
            "quality_score": quality_score,
            "pipeline_batch_id": batch_id,
            "published_at": f"{batch_id}T09:00:00Z",
            "pipeline_model": settings.openai_model_main,
            "translation_group_id": translation_group_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

        # Build guide_items with persona-specific quizzes and code-extracted sources
        guide_items: dict[str, Any] = {}
        for pname in ("expert", "learner"):
            quiz = persona_quizzes.get(pname, {}).get("en" if locale == "en" else "ko")
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
        if guide_items:
            row["guide_items"] = guide_items

        try:
            supabase.table("news_posts").upsert(row, on_conflict="slug").execute()
            posts_created += 1
            logger.info("Saved %s %s digest draft: %s", digest_type, locale, slug)
        except Exception as e:
            error_msg = f"Failed to save {digest_type} {locale} digest: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    await _log_stage(
        supabase, run_id, f"save:{digest_type}",
        "success" if posts_created > 0 else "failed", t_save,
        output_summary=f"{posts_created} digest rows saved",
        post_type=digest_type,
        debug_meta={"slug_base": slug_base, "locales": ["en", "ko"]},
    )

    return posts_created, errors, cumulative_usage



async def run_daily_pipeline(
    batch_id: str | None = None,
    target_date: str | None = None,
    skip_handbook: bool = False,
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

    run_id = str(uuid.uuid4())
    try:
        supabase.table("pipeline_runs").insert({
            "id": run_id,
            "run_key": f"news-{batch_id}",
            "status": "running",
        }).execute()
    except Exception as e:
        logger.warning("Pipeline run already exists for %s, skipping: %s", batch_id, e)
        return PipelineResult(batch_id=batch_id, status="skipped", message=f"Duplicate run: {batch_id}")

    try:
        # Fetch recently published source URLs to avoid repeating news
        published_urls: set[str] = set()
        try:
            recent = supabase.table("news_posts").select("source_urls") \
                .gte("created_at", (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()) \
                .execute()
            for row in (recent.data or []):
                for url in (row.get("source_urls") or []):
                    published_urls.add(url)
        except Exception as e:
            logger.warning("Failed to fetch published URLs: %s", e)

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
        classification, classify_usage = await classify_candidates(candidates)
        cumulative_usage = merge_usage_metrics(cumulative_usage, classify_usage)

        classify_input_summary = "\n".join(
            f"[{i+1}] {c.title} ({c.url})" for i, c in enumerate(candidates)
        )
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
        if community_lookup:
            community_tasks = [
                collect_community_reactions(title, url)
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
                    community_map=community_map,
                    supabase=supabase,
                    run_id=run_id,
                    enriched_map=enriched_map,
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
        status = "success" if not all_errors else "failed"

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
    from models.news_pipeline import ClassifiedCandidate, ClassificationResult, NewsCandidate

    supabase = get_supabase()
    run_id = source_run_id  # Reuse existing run

    # Delete logs from the rerun stage onward
    STAGE_CASCADE = {
        "classify": ["classify", "merge", "community", "ranking", "enrich",
                      "digest:research:expert", "digest:research:learner",
                      "digest:business:expert", "digest:business:learner",
                      "quality:research", "quality:business",
                      "save:research", "save:business", "summary"],
        "merge": ["merge", "community", "ranking", "enrich",
                  "digest:research:expert", "digest:research:learner",
                  "digest:business:expert", "digest:business:learner",
                  "quality:research", "quality:business",
                  "save:research", "save:business", "summary"],
        "community": ["community", "ranking", "enrich",
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
    try:
        for stage_name in stages_to_delete:
            supabase.table("pipeline_logs").delete().eq("run_id", run_id).eq("pipeline_type", stage_name).execute()
        supabase.table("pipeline_runs").update({
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "last_error": None,
        }).eq("id", run_id).execute()
    except Exception as e:
        return PipelineResult(batch_id=batch_id, status="failed", message=f"Failed to prepare rerun: {e}")

    cumulative_usage: dict[str, Any] = {}
    all_errors: list[str] = []
    total_posts = 0

    try:
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
            classification, classify_usage = await classify_candidates(candidates)
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
            if community_lookup:
                community_tasks = [collect_community_reactions(t, u) for t, u in community_lookup]
                community_results = await asyncio.gather(*community_tasks, return_exceptions=True)
                for (_, url), result in zip(community_lookup, community_results):
                    if isinstance(result, str) and result.strip():
                        community_map[url] = result
            _save_checkpoint(supabase, run_id, "community", {"community_map": community_map})
            await _log_stage(supabase, run_id, "community", "success", t0,
                             output_summary=f"{len(community_map)} reactions")

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
                    community_map=community_map,
                    supabase=supabase,
                    run_id=run_id,
                    enriched_map=enriched_map,
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

        status = "success" if total_posts > 0 else "failed"
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
            if p.get("content_expert")
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

    try:
        supabase.table("pipeline_runs").insert({
            "id": run_id,
            "run_key": run_key,
            "status": "running",
        }).execute()
    except Exception as e:
        logger.warning("Handbook extraction run already exists for %s, skipping: %s", batch_id, e)
        return PipelineResult(batch_id=batch_id, status="skipped", message=f"Duplicate handbook run: {batch_id}")

    try:
        terms_created, errors = await _extract_and_create_handbook_terms(
            article_texts, supabase, run_id,
        )
        all_errors.extend(errors)

        status = "success" if not errors else ("partial" if terms_created > 0 else "failed")
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
        batch_id=batch_id,
        posts_created=0,
        errors=all_errors,
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
        .gte("created_at", monday.isoformat())
        .lte("created_at", sunday.isoformat() + "T23:59:59")
        .order("created_at", desc=False)
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
        .select("slug, term, korean_term, definition_en, definition_ko")
        .eq("status", "published")
        .gte("created_at", monday.isoformat())
        .lte("created_at", sunday.isoformat() + "T23:59:59")
        .limit(3)
        .execute()
    )
    return result.data or []


async def run_weekly_pipeline(
    week_id: str | None = None,
) -> PipelineResult:
    """Generate weekly recap from Mon-Fri daily digests.

    Flow: fetch week's dailies -> LLM weekly summary (expert/learner x EN/KO) -> save draft.
    """
    from services.agents.prompts_news_pipeline import get_weekly_prompt

    if week_id is None:
        last_week = datetime.strptime(today_kst(), "%Y-%m-%d").date() - timedelta(days=7)
        week_id = _iso_week_id(last_week)

    supabase = get_supabase()
    if not supabase:
        return PipelineResult(batch_id=week_id, errors=["Supabase not configured"])

    run_id = str(uuid.uuid4())
    try:
        supabase.table("pipeline_runs").insert({
            "id": run_id,
            "run_key": f"weekly-{week_id}",
            "status": "running",
        }).execute()
    except Exception as e:
        logger.warning("Weekly run already exists for %s: %s", week_id, e)
        return PipelineResult(batch_id=week_id, status="skipped", message=f"Duplicate: {week_id}")

    all_errors: list[str] = []
    cumulative_usage: dict[str, Any] = {}
    total_posts = 0

    try:
        for locale in ("en", "ko"):
            language = "English" if locale == "en" else "Korean"

            # Fetch daily digests for the week
            digests = await _fetch_week_digests(supabase, week_id, locale)
            if not digests:
                all_errors.append(f"No daily digests for {week_id} {locale}")
                continue

            # Build per-persona input text (avoid tone contamination + save tokens)
            persona_daily_texts: dict[str, str] = {}
            for persona in ("expert", "learner"):
                content_key = f"content_{persona}"
                text = ""
                for d in digests:
                    content = d.get(content_key, "")
                    if not content:
                        continue
                    text += f"\n\n--- {d['post_type'].upper()} ({d.get('published_at', '')}) ---\n"
                    text += f"# {d['title']}\n\n{content}\n"
                persona_daily_texts[persona] = text

            # Fetch handbook terms for bottom card
            week_terms = await _fetch_week_handbook_terms(supabase, week_id, locale)

            # Generate per persona (expert + learner) in parallel
            personas: dict[str, dict] = {}
            client = get_openai_client()

            async def _gen_weekly_persona(persona: str) -> None:
                daily_text = persona_daily_texts.get(persona, "")
                if not daily_text:
                    return
                t_p = time.monotonic()
                system_prompt = get_weekly_prompt(persona, language)
                try:
                    response = await asyncio.wait_for(
                        client.chat.completions.create(
                            model=settings.openai_model_main,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": daily_text},
                            ],
                            temperature=0.5,
                            max_tokens=6000,
                        ),
                        timeout=120,
                    )

                    raw = response.choices[0].message.content or ""
                    usage = extract_usage_metrics(response)
                    merge_usage_metrics(cumulative_usage, usage)

                    # Parse JSON block from end of response
                    json_data = {}
                    if "```json" in raw:
                        json_str = raw.split("```json")[-1].split("```")[0].strip()
                        json_data = parse_ai_json(json_str, f"weekly-{persona}-{locale}")
                        content = raw[:raw.rfind("```json")].strip()
                    else:
                        content = raw

                    personas[persona] = {"content": content, "json_data": json_data}

                    await _log_stage(
                        supabase, run_id, f"weekly:{persona}:{locale}", "success", t_p,
                        usage=usage, post_type="weekly", locale=locale,
                    )

                except Exception as e:
                    logger.warning("Weekly %s %s %s failed: %s", week_id, persona, locale, e)
                    all_errors.append(f"weekly {persona} {locale}: {e}")
                    await _log_stage(
                        supabase, run_id, f"weekly:{persona}:{locale}", "failed", t_p,
                        error_message=str(e), post_type="weekly", locale=locale,
                    )

            await asyncio.gather(
                _gen_weekly_persona("expert"),
                _gen_weekly_persona("learner"),
            )

            if not personas:
                continue

            # Build row
            expert_data = personas.get("expert", {})
            learner_data = personas.get("learner", {})
            expert_json = expert_data.get("json_data", {})
            learner_json = learner_data.get("json_data", {})

            headline = expert_json.get("headline") or learner_json.get("headline") or f"AI Weekly — {week_id}"

            slug = f"{week_id.lower()}-weekly-digest" if locale == "en" else f"{week_id.lower()}-weekly-digest-ko"

            # Reading time
            text = expert_data.get("content", "") or learner_data.get("content", "")
            if locale == "ko":
                char_count = len([c for c in text if c.strip() and c not in '.,!?;:()[]{}"\'-\u2014\u2026#*_~`|/>'])
                reading_time = max(1, round(char_count / 500))
            else:
                reading_time = max(1, round(len(text.split()) / 200))

            guide_items = {
                "week_numbers": expert_json.get("week_numbers", []),
                "week_tool": expert_json.get("week_tool") or learner_json.get("week_tool", {}),
                "week_terms": [
                    {
                        "slug": t["slug"],
                        "term": t.get("korean_term" if locale == "ko" else "term") or t.get("term", ""),
                        "definition": t.get(f"definition_{locale}", ""),
                    }
                    for t in week_terms[:2]
                ],
            }

            row = {
                "title": headline,
                "slug": slug,
                "locale": locale,
                "category": "ai-news",
                "post_type": "weekly",
                "status": "draft",
                "content_expert": expert_data.get("content", ""),
                "content_learner": learner_data.get("content", ""),
                "pipeline_batch_id": week_id,
                "reading_time_min": reading_time,
                "guide_items": guide_items,
            }

            try:
                supabase.table("news_posts").upsert(
                    row, on_conflict="slug,locale"
                ).execute()
                total_posts += 1
                logger.info("Saved weekly %s draft: %s", locale, slug)
            except Exception as e:
                all_errors.append(f"Save weekly {locale}: {e}")

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
            "summary": {"total_posts": total_posts, "errors": all_errors},
        }).eq("id", run_id).execute()

        return PipelineResult(
            batch_id=week_id,
            status=status,
            total_posts=total_posts,
            errors=all_errors,
            usage=cumulative_usage,
        )

    except Exception as e:
        logger.error("Weekly pipeline failed: %s", e, exc_info=True)
        try:
            supabase.table("pipeline_runs").update({
                "status": "failed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "summary": {"error": str(e)},
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

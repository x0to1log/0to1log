"""AI News Pipeline v2 orchestrator."""
import logging
import time
import uuid
from datetime import date, datetime, timezone
from typing import Any

from core.config import settings
from core.database import get_supabase
from models.news_pipeline import (
    PersonaOutput,
    PipelineResult,
    RankedCandidate,
)
from services.agents.advisor import extract_terms_from_content, generate_term_content
from services.agents.client import merge_usage_metrics
from services.agents.fact_extractor import extract_facts
from services.agents.persona_writer import write_persona
from services.agents.ranking import rank_candidates
from services.news_collection import collect_community_reactions, collect_news

logger = logging.getLogger(__name__)


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

    try:
        supabase.table("pipeline_logs").insert({
            "run_id": run_id,
            "pipeline_type": stage,
            "status": status,
            "input_summary": input_summary,
            "output_summary": output_summary,
            "error_message": error_message,
            "duration_ms": duration_ms,
            "model_used": usage.get("model_used"),
            "tokens_used": usage.get("tokens_used"),
            "cost_usd": usage.get("cost_usd"),
            "post_type": post_type,
            "locale": locale,
            "attempt": attempt,
            "debug_meta": meta or None,
        }).execute()
    except Exception as e:
        logger.warning("Failed to log stage %s: %s", stage, e)


def _trim(text: str | None, max_len: int = 1000) -> str:
    """Trim text to max_len for debug_meta storage."""
    if not text:
        return ""
    return text[:max_len] + ("..." if len(text) > max_len else "")


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
        extracted, extract_model, extract_tokens = await extract_terms_from_content(combined)
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
        debug_meta={
            "terms": [t.get("term", "") for t in extracted],
            "model": extract_model,
            "tokens": extract_tokens,
        },
    )

    if not extracted:
        return 0, []

    # Step 2: Check duplicates and generate content for new terms
    for term_info in extracted:
        term_name = term_info.get("term", "").strip()
        korean_name = term_info.get("korean_name", "").strip()
        if not term_name:
            continue

        slug = _slugify(term_name)
        if not slug:
            continue

        # Check if term already exists
        try:
            existing = (
                supabase.table("handbook_terms")
                .select("id")
                .or_(f"slug.eq.{slug},term.ilike.{term_name}")
                .limit(1)
                .execute()
            )
            if existing.data:
                logger.info("Handbook term '%s' already exists, skipping", term_name)
                continue
        except Exception as e:
            logger.warning("Duplicate check failed for '%s': %s", term_name, e)
            continue

        # Generate content (2 LLM calls)
        t_gen = time.monotonic()
        try:
            content_data, gen_model, gen_tokens = await generate_term_content(
                term_name, korean_name,
            )
        except Exception as e:
            error_msg = f"Handbook generate failed for '{term_name}': {e}"
            logger.warning(error_msg)
            errors.append(error_msg)
            await _log_stage(
                supabase, run_id, "handbook.auto_generate", "failed", t_gen,
                error_message=error_msg,
                debug_meta={"term": term_name},
            )
            continue

        # Insert as draft
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
                "status": "draft",
                "source": "pipeline",
            }
            supabase.table("handbook_terms").insert(row).execute()
            terms_created += 1
            logger.info("Created handbook draft: %s (%s)", term_name, slug)

            await _log_stage(
                supabase, run_id, "handbook.auto_generate", "success", t_gen,
                output_summary=f"term={term_name}, slug={slug}",
                debug_meta={
                    "term": term_name,
                    "slug": slug,
                    "model": gen_model,
                    "tokens": gen_tokens,
                },
            )
        except Exception as e:
            error_msg = f"Failed to save handbook term '{term_name}': {e}"
            logger.warning(error_msg)
            errors.append(error_msg)

    logger.info("Handbook auto-extraction: %d terms created, %d errors", terms_created, len(errors))
    return terms_created, errors


async def _generate_post(
    candidate: RankedCandidate,
    post_type: str,
    batch_id: str,
    handbook_slugs: list[str],
    supabase,
    run_id: str,
    raw_content: str = "",
) -> tuple[int, list[str], dict[str, Any]]:
    """Generate a single post (fact extraction + 3 personas + save EN/KO).

    Returns (posts_created, errors, usage).
    """
    errors: list[str] = []
    cumulative_usage: dict[str, Any] = {}
    posts_created = 0

    # Step 1: Collect community reactions
    try:
        reactions = await collect_community_reactions(candidate.title, candidate.url)
    except Exception as e:
        logger.warning("Community reactions failed for %s: %s", candidate.title, e)
        reactions = ""

    # Step 2: Extract facts
    t0 = time.monotonic()
    try:
        MAX_ARTICLE_CHARS = 8000
        article_body = (raw_content or candidate.snippet)[:MAX_ARTICLE_CHARS]
        news_text = f"Title: {candidate.title}\nURL: {candidate.url}\n\n{article_body}"
        fact_pack, fact_usage = await extract_facts(
            news_text=news_text,
            context_text=candidate.snippet,
            community_text=reactions,
        )
        cumulative_usage = merge_usage_metrics(cumulative_usage, fact_usage)
        fact_pack_json = fact_pack.model_dump()

        await _log_stage(
            supabase, run_id, f"facts:{post_type}", "success", t0,
            input_summary=_trim(news_text),
            output_summary=f"headline: {fact_pack.headline}, {len(fact_pack.key_facts)} facts",
            usage=fact_usage,
            post_type=post_type,
            attempt=fact_usage.get("attempts"),
            debug_meta={
                "llm_input": _trim(news_text),
                "llm_output": fact_pack_json,
                "attempts": fact_usage.get("attempts"),
            },
        )
    except Exception as e:
        error_msg = f"{post_type} fact extraction failed: {e}"
        logger.error(error_msg)
        errors.append(error_msg)
        await _log_stage(
            supabase, run_id, f"facts:{post_type}", "failed", t0,
            error_message=error_msg, post_type=post_type,
        )
        return 0, errors, cumulative_usage

    # Step 3: Write all 3 personas (log each individually)
    for persona_name in ("expert", "learner", "beginner"):
        t_p = time.monotonic()
        try:
            persona_output, persona_usage = await write_persona(
                persona=persona_name,
                fact_pack=fact_pack,
                handbook_slugs=handbook_slugs,
                post_type=post_type,
            )
            cumulative_usage = merge_usage_metrics(cumulative_usage, persona_usage)

            await _log_stage(
                supabase, run_id,
                f"persona:{post_type}:{persona_name}", "success", t_p,
                output_summary=f"en={len(persona_output.en)}chars, ko={len(persona_output.ko)}chars",
                usage=persona_usage,
                post_type=post_type,
                attempt=persona_usage.get("attempts"),
                debug_meta={
                    "attempts": persona_usage.get("attempts"),
                    "en_length": len(persona_output.en),
                    "ko_length": len(persona_output.ko),
                    "en_preview": _trim(persona_output.en, 500),
                    "ko_preview": _trim(persona_output.ko, 500),
                },
            )

            # Store for later save
            if not hasattr(fact_pack, '_personas'):
                fact_pack._personas = {}
            fact_pack._personas[persona_name] = persona_output

        except Exception as e:
            error_msg = f"{post_type} {persona_name} writing failed: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            await _log_stage(
                supabase, run_id,
                f"persona:{post_type}:{persona_name}", "failed", t_p,
                error_message=error_msg, post_type=post_type,
            )

    personas: dict[str, PersonaOutput] = getattr(fact_pack, '_personas', {})
    if not personas:
        return 0, errors, cumulative_usage

    # Step 4: Save EN + KO rows
    t_save = time.monotonic()
    translation_group_id = str(uuid.uuid4())
    base_slug = _slugify(fact_pack.headline or candidate.title)

    source_cards = [s.model_dump() for s in fact_pack.sources]
    source_urls = [s.url for s in fact_pack.sources if s.url]

    for locale in ("en", "ko"):
        slug_suffix = "" if locale == "en" else "-ko"
        slug = f"{batch_id}-{base_slug}{slug_suffix}"

        title = (fact_pack.headline_ko or fact_pack.headline or candidate.title) if locale == "ko" \
            else (fact_pack.headline or candidate.title)
        row = {
            "title": title,
            "slug": slug,
            "locale": locale,
            "category": "ai-news",
            "post_type": post_type,
            "status": "draft",
            "content_expert": personas.get("expert", PersonaOutput()).en if locale == "en"
                else personas.get("expert", PersonaOutput()).ko,
            "content_learner": personas.get("learner", PersonaOutput()).en if locale == "en"
                else personas.get("learner", PersonaOutput()).ko,
            "content_beginner": personas.get("beginner", PersonaOutput()).en if locale == "en"
                else personas.get("beginner", PersonaOutput()).ko,
            "fact_pack": fact_pack_json,
            "source_cards": source_cards,
            "source_urls": source_urls,
            "pipeline_batch_id": batch_id,
            "pipeline_model": settings.openai_model_main,
            "pipeline_tokens": cumulative_usage.get("tokens_used") if locale == "en" else None,
            "pipeline_cost": cumulative_usage.get("cost_usd") if locale == "en" else None,
            "translation_group_id": translation_group_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            supabase.table("news_posts").upsert(row).execute()
            posts_created += 1
            logger.info("Saved %s %s draft: %s", post_type, locale, slug)
        except Exception as e:
            error_msg = f"Failed to save {post_type} {locale}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    save_status = "success" if posts_created > 0 else "failed"
    await _log_stage(
        supabase, run_id, f"save:{post_type}", save_status, t_save,
        output_summary=f"{posts_created} rows saved",
        post_type=post_type,
        debug_meta={
            "slug_base": f"{batch_id}-{base_slug}",
            "locales": ["en", "ko"],
        },
    )

    return posts_created, errors, cumulative_usage


async def run_daily_pipeline(
    batch_id: str | None = None,
    target_date: str | None = None,
) -> PipelineResult:
    """Run the full daily AI news pipeline.

    Flow: collect → rank → (react + extract + personas) × 2 → save drafts.
    """
    if batch_id is None:
        batch_id = target_date or date.today().isoformat()

    is_backfill = False
    if target_date:
        try:
            is_backfill = datetime.strptime(target_date, "%Y-%m-%d").date() < date.today()
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
            "run_key": f"news-v2-{batch_id}",
            "status": "running",
        }).execute()
    except Exception as e:
        logger.warning("Failed to record pipeline run: %s", e)

    try:
        # Stage: collect
        t0 = time.monotonic()
        candidates, collect_meta = await collect_news(target_date=target_date)

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

        # Stage: rank
        t0 = time.monotonic()
        ranking, rank_usage = await rank_candidates(candidates)
        cumulative_usage = merge_usage_metrics(cumulative_usage, rank_usage)

        # Build LLM input summary for quality inspection
        rank_input_summary = "\n".join(
            f"[{i+1}] {c.title} ({c.url})" for i, c in enumerate(candidates)
        )
        rank_output = {
            "research": {
                "title": ranking.research.title,
                "url": ranking.research.url,
                "score": ranking.research.relevance_score,
                "reason": ranking.research.ranking_reason,
            } if ranking.research else None,
            "business": {
                "title": ranking.business.title,
                "url": ranking.business.url,
                "score": ranking.business.relevance_score,
                "reason": ranking.business.ranking_reason,
            } if ranking.business else None,
        }

        await _log_stage(
            supabase, run_id, "rank", "success", t0,
            input_summary=f"{len(candidates)} candidates",
            output_summary=f"research={'yes' if ranking.research else 'no'}, business={'yes' if ranking.business else 'no'}",
            usage=rank_usage,
            debug_meta={
                "llm_input": _trim(rank_input_summary),
                "llm_output": rank_output,
                "candidates_count": len(candidates),
                "attempts": rank_usage.get("attempts"),
            },
        )

        handbook_slugs = _fetch_handbook_slugs(supabase)

        # Build URL→raw_content lookup from original candidates
        raw_content_map = {c.url: c.raw_content for c in candidates if c.raw_content}

        picks = []
        if ranking.research:
            picks.append(("research", ranking.research))
        if ranking.business:
            picks.append(("business", ranking.business))

        for post_type, candidate in picks:
            raw_content = raw_content_map.get(candidate.url, "")
            posts, errors, usage = await _generate_post(
                candidate=candidate,
                post_type=post_type,
                batch_id=batch_id,
                handbook_slugs=handbook_slugs,
                supabase=supabase,
                run_id=run_id,
                raw_content=raw_content,
            )
            total_posts += posts
            all_errors.extend(errors)
            cumulative_usage = merge_usage_metrics(cumulative_usage, usage)

        # Stage: handbook term extraction
        handbook_terms_created = 0
        article_texts = [
            raw_content_map.get(candidate.url, "")
            for _, candidate in picks
            if raw_content_map.get(candidate.url, "")
        ]
        if article_texts:
            try:
                handbook_terms_created, handbook_errors = await _extract_and_create_handbook_terms(
                    article_texts, supabase, run_id,
                )
                all_errors.extend(handbook_errors)
            except Exception as e:
                logger.warning("Handbook extraction stage failed: %s", e)

        # Stage: summary
        t_summary = time.monotonic()
        status = "success" if not all_errors else "failed"

        await _log_stage(
            supabase, run_id, "summary", status, t_summary,
            input_summary=f"{len(candidates)} candidates, {len(picks)} selected",
            output_summary=f"{total_posts} posts created, {handbook_terms_created} handbook terms",
            usage=cumulative_usage,
            error_message="; ".join(all_errors) if all_errors else None,
            debug_meta={
                "mode": "backfill" if is_backfill else "daily",
                "target_date": target_date,
                "batch_id": batch_id,
                "total_posts": total_posts,
                "handbook_terms_created": handbook_terms_created,
                "total_cost": cumulative_usage.get("cost_usd"),
                "picks": [pt for pt, _ in picks],
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
    logger.info("Pipeline complete: %d posts, %d errors", total_posts, len(all_errors))
    return result

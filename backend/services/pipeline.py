"""AI News Pipeline v2 orchestrator."""
import logging
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
from services.agents.client import merge_usage_metrics
from services.agents.fact_extractor import extract_facts
from services.agents.persona_writer import write_all_personas
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


async def _generate_post(
    candidate: RankedCandidate,
    post_type: str,
    batch_id: str,
    handbook_slugs: list[str],
    supabase,
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
    try:
        news_text = f"Title: {candidate.title}\nURL: {candidate.url}\n\n{candidate.snippet}"
        fact_pack, fact_usage = await extract_facts(
            news_text=news_text,
            context_text=candidate.snippet,
            community_text=reactions,
        )
        cumulative_usage = merge_usage_metrics(cumulative_usage, fact_usage)
    except Exception as e:
        error_msg = f"{post_type} fact extraction failed: {e}"
        logger.error(error_msg)
        errors.append(error_msg)
        return 0, errors, cumulative_usage

    # Step 3: Write all 3 personas
    try:
        personas, persona_usage = await write_all_personas(
            fact_pack=fact_pack,
            handbook_slugs=handbook_slugs,
            post_type=post_type,
        )
        cumulative_usage = merge_usage_metrics(cumulative_usage, persona_usage)
    except Exception as e:
        error_msg = f"{post_type} persona writing failed: {e}"
        logger.error(error_msg)
        errors.append(error_msg)
        return 0, errors, cumulative_usage

    # Step 4: Save EN + KO rows
    translation_group_id = str(uuid.uuid4())
    base_slug = _slugify(fact_pack.headline or candidate.title)

    source_cards = [s.model_dump() for s in fact_pack.sources]
    source_urls = [s.url for s in fact_pack.sources if s.url]
    fact_pack_json = fact_pack.model_dump()

    for locale in ("en", "ko"):
        slug_suffix = "" if locale == "en" else "-ko"
        slug = f"{batch_id}-{base_slug}{slug_suffix}"

        row = {
            "title": fact_pack.headline or candidate.title,
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

    return posts_created, errors, cumulative_usage


async def run_daily_pipeline(
    batch_id: str | None = None,
) -> PipelineResult:
    """Run the full daily AI news pipeline.

    Flow: collect → rank → (react + extract + personas) × 2 → save drafts.
    """
    if batch_id is None:
        batch_id = date.today().isoformat()

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
        candidates = await collect_news()
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

        ranking, rank_usage = await rank_candidates(candidates)
        cumulative_usage = merge_usage_metrics(cumulative_usage, rank_usage)

        handbook_slugs = _fetch_handbook_slugs(supabase)

        picks = []
        if ranking.research:
            picks.append(("research", ranking.research))
        if ranking.business:
            picks.append(("business", ranking.business))

        for post_type, candidate in picks:
            posts, errors, usage = await _generate_post(
                candidate=candidate,
                post_type=post_type,
                batch_id=batch_id,
                handbook_slugs=handbook_slugs,
                supabase=supabase,
            )
            total_posts += posts
            all_errors.extend(errors)
            cumulative_usage = merge_usage_metrics(cumulative_usage, usage)

        status = "success" if not all_errors else "failed"
        try:
            supabase.table("pipeline_runs").update({
                "status": status,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "last_error": all_errors[0] if all_errors else None,
            }).eq("id", run_id).execute()
        except Exception as e:
            logger.warning("Failed to update pipeline run: %s", e)

        try:
            supabase.table("pipeline_logs").insert({
                "run_id": run_id,
                "pipeline_type": "news-v2",
                "status": status,
                "input_summary": f"{len(candidates)} candidates, {len(picks)} selected",
                "output_summary": f"{total_posts} posts created",
                "model_used": cumulative_usage.get("model_used"),
                "tokens_used": cumulative_usage.get("tokens_used"),
                "cost_usd": cumulative_usage.get("cost_usd"),
                "error_message": "; ".join(all_errors) if all_errors else None,
            }).execute()
        except Exception as e:
            logger.warning("Failed to log pipeline execution: %s", e)

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

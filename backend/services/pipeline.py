import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from core.database import get_supabase
from services.news_collection import collect_all_news
from services.agents import rank_candidates, generate_research_post, generate_business_post
from models.ranking import NewsCandidate, NewsRankingResult
from models.research import ResearchPost
from models.business import BusinessPost

logger = logging.getLogger(__name__)

STALE_THRESHOLD_SECONDS = 3600  # 1 hour


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _parse_dt(dt_str: str) -> datetime:
    """Parse ISO datetime string to timezone-aware datetime."""
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _build_context(candidates: list[NewsCandidate]) -> str:
    """Build a context string from collected candidates for writing agents."""
    lines: list[str] = []
    for i, c in enumerate(candidates, 1):
        lines.append(f"{i}. [{c.source}] {c.title}\n   URL: {c.url}\n   {c.snippet}")
    return "\n\n".join(lines)


async def acquire_pipeline_lock(batch_id: str) -> Optional[str]:
    """Attempt to acquire a pipeline lock for the given batch.

    Returns run_id if lock acquired, None if skipped.

    Lock rules:
    - success → skip (already done)
    - running < 1h → skip (in progress)
    - running >= 1h → UPDATE existing row (stale recovery)
    - failed → UPDATE existing row (retry)
    - no record → INSERT new row
    """
    client = get_supabase()
    if not client:
        logger.error("Supabase not configured, cannot acquire lock")
        return None

    run_key = f"daily:{batch_id}"

    existing = (
        client.table("pipeline_runs")
        .select("*")
        .eq("run_key", run_key)
        .maybe_single()
        .execute()
    )

    row = existing.data if existing else None
    if row:
        status = row["status"]

        if status == "success":
            logger.info("Pipeline %s already succeeded, skipping", run_key)
            return None

        if status == "running":
            started = _parse_dt(row["started_at"])
            elapsed = (_now() - started).total_seconds()
            if elapsed < STALE_THRESHOLD_SECONDS:
                logger.info("Pipeline %s still running (%ds), skipping", run_key, int(elapsed))
                return None
            # Stale lock: UPDATE existing row to reclaim
            logger.warning("Pipeline %s stale (%.0fs), recovering lock", run_key, elapsed)
            client.table("pipeline_runs").update({
                "status": "running",
                "started_at": _now_iso(),
                "finished_at": None,
                "last_error": "stale lock recovered",
            }).eq("run_key", run_key).execute()
            return row["id"]

        if status == "failed":
            # Failed: UPDATE existing row for retry
            logger.info("Pipeline %s previously failed, retrying", run_key)
            client.table("pipeline_runs").update({
                "status": "running",
                "started_at": _now_iso(),
                "finished_at": None,
                "last_error": None,
            }).eq("run_key", run_key).execute()
            return row["id"]

    # No existing record: INSERT new
    result = (
        client.table("pipeline_runs")
        .insert({"run_key": run_key, "status": "running"})
        .execute()
    )
    run_id = result.data[0]["id"]
    logger.info("Pipeline lock acquired: %s (run_id=%s)", run_key, run_id)
    return run_id


async def release_pipeline_lock(
    run_id: str,
    status: str,
    error: Optional[str] = None,
) -> None:
    """Release a pipeline lock by updating its status."""
    client = get_supabase()
    if not client:
        return

    update_data = {
        "status": status,
        "finished_at": _now_iso(),
    }
    if error:
        update_data["last_error"] = error

    client.table("pipeline_runs").update(update_data).eq("id", run_id).execute()
    logger.info("Pipeline lock released: run_id=%s status=%s", run_id, status)


def _save_candidates(
    candidates: list[NewsCandidate],
    ranking: NewsRankingResult,
    batch_id: str,
) -> None:
    """Save ranked candidates to news_candidates table."""
    client = get_supabase()
    if not client:
        return

    # Build a lookup of assigned types from ranking result
    assigned: dict[str, tuple[str, float, str]] = {}  # url → (type, score, reason)
    for pick, ptype in [
        (ranking.research_pick, "research"),
        (ranking.business_main_pick, "business_main"),
    ]:
        if pick:
            assigned[pick.url] = (ptype, pick.relevance_score, pick.ranking_reason)
    if ranking.related_picks:
        for ptype, pick in [
            ("big_tech", ranking.related_picks.big_tech),
            ("industry_biz", ranking.related_picks.industry_biz),
            ("new_tools", ranking.related_picks.new_tools),
        ]:
            if pick:
                assigned[pick.url] = (ptype, pick.relevance_score, pick.ranking_reason)

    rows = []
    for c in candidates:
        info = assigned.get(c.url)
        rows.append({
            "batch_id": batch_id,
            "title": c.title,
            "url": c.url,
            "snippet": c.snippet,
            "source": c.source,
            "assigned_type": info[0] if info else None,
            "relevance_score": info[1] if info else None,
            "ranking_reason": info[2] if info else None,
            "status": "selected" if info else "pending",
        })

    client.table("news_candidates").insert(rows).execute()
    logger.info("Saved %d candidates to news_candidates", len(rows))


def _save_research_post(post: ResearchPost, batch_id: str) -> str:
    """Save research post to posts table. Returns the post id."""
    client = get_supabase()
    if not client:
        return ""

    translation_group_id = str(uuid.uuid4())
    row = {
        "title": post.title,
        "slug": post.slug,
        "locale": "ko",
        "category": "ai-news",
        "post_type": "research",
        "status": "draft",
        "content_original": post.content_original,
        "no_news_notice": post.no_news_notice,
        "recent_fallback": post.recent_fallback,
        "guide_items": post.guide_items.model_dump() if post.guide_items else None,
        "source_urls": post.source_urls,
        "news_temperature": post.news_temperature,
        "tags": post.tags,
        "pipeline_batch_id": batch_id,
        "translation_group_id": translation_group_id,
    }

    result = client.table("posts").upsert(row, on_conflict="slug").execute()
    post_id = result.data[0]["id"]
    logger.info("Research post saved: id=%s slug=%s", post_id, post.slug)
    return post_id


def _save_business_post(post: BusinessPost, batch_id: str) -> str:
    """Save business post to posts table. Returns the post id."""
    client = get_supabase()
    if not client:
        return ""

    translation_group_id = str(uuid.uuid4())
    row = {
        "title": post.title,
        "slug": post.slug,
        "locale": "ko",
        "category": "ai-news",
        "post_type": "business",
        "status": "draft",
        "content_beginner": post.content_beginner,
        "content_learner": post.content_learner,
        "content_expert": post.content_expert,
        "guide_items": post.guide_items.model_dump() if post.guide_items else None,
        "related_news": post.related_news.model_dump() if post.related_news else None,
        "source_urls": post.source_urls,
        "news_temperature": post.news_temperature,
        "tags": post.tags,
        "pipeline_batch_id": batch_id,
        "translation_group_id": translation_group_id,
    }

    result = client.table("posts").upsert(row, on_conflict="slug").execute()
    post_id = result.data[0]["id"]
    logger.info("Business post saved: id=%s slug=%s", post_id, post.slug)
    return post_id


async def run_daily_pipeline(batch_id: str) -> None:
    """Main pipeline orchestrator: collect → rank → generate → save to DB."""
    run_id = await acquire_pipeline_lock(batch_id)
    if not run_id:
        return

    try:
        logger.info("Pipeline %s started (run_id=%s)", batch_id, run_id)

        # Step 1: Collect news from all sources
        candidates = await collect_all_news(batch_id)
        if not candidates:
            logger.warning("No candidates for batch %s, finishing early", batch_id)
            await release_pipeline_lock(run_id, "success")
            return

        # Step 2: Rank candidates
        ranking = await rank_candidates(candidates)

        # Step 2b: Save candidates + ranking to DB
        try:
            _save_candidates(candidates, ranking, batch_id)
        except Exception as e:
            logger.error("Failed to save candidates (non-fatal): %s", e)

        # Build context string from candidates for the writing agents
        context = _build_context(candidates)

        # Step 3-A: Generate research post
        research_post = await generate_research_post(
            ranking.research_pick, context, batch_id
        )
        logger.info("Research post generated: %s", research_post.title)
        _save_research_post(research_post, batch_id)

        # Step 3-B: Generate business post (skip if no business pick)
        if ranking.business_main_pick:
            business_post = await generate_business_post(
                ranking.business_main_pick, ranking.related_picks, context, batch_id
            )
            logger.info("Business post generated: %s", business_post.title)
            _save_business_post(business_post, batch_id)
        else:
            logger.warning("No business_main_pick for batch %s, skipping business post", batch_id)

        logger.info("Pipeline %s completed — posts saved to DB", batch_id)
        await release_pipeline_lock(run_id, "success")
    except Exception as e:
        logger.error("Pipeline %s failed: %s", batch_id, e)
        await release_pipeline_lock(run_id, "failed", str(e))
        raise

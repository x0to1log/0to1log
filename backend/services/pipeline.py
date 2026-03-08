import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from core.database import get_supabase
from services.news_collection import collect_all_news
from services.agents import rank_candidates, generate_research_post, generate_business_post
from models.ranking import NewsCandidate

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


async def run_daily_pipeline(batch_id: str) -> None:
    """Main pipeline orchestrator: collect → rank → generate research & business posts."""
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

        # Build context string from candidates for the writing agents
        context = _build_context(candidates)

        # Step 3-A: Generate research post
        research_post = await generate_research_post(
            ranking.research_pick, context, batch_id
        )
        logger.info("Research post generated: %s", research_post.title)

        # Step 3-B: Generate business post
        business_post = await generate_business_post(
            ranking.business_main_pick, ranking.related_picks, context, batch_id
        )
        logger.info("Business post generated: %s", business_post.title)

        logger.info("Pipeline %s completed", batch_id)
        await release_pipeline_lock(run_id, "success")
    except Exception as e:
        logger.error("Pipeline %s failed: %s", batch_id, e)
        await release_pipeline_lock(run_id, "failed", str(e))
        raise

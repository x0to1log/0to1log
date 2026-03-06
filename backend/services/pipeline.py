import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from core.database import get_supabase

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

    if existing.data:
        row = existing.data
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
    """Main pipeline orchestrator. Phase 2A: lock management only.
    Phase 2B will add: collect → rank → generate → save → editorial.
    """
    run_id = await acquire_pipeline_lock(batch_id)
    if not run_id:
        return

    try:
        # Phase 2B: actual pipeline steps here
        logger.info("Pipeline %s started (run_id=%s) — stub", batch_id, run_id)
        await release_pipeline_lock(run_id, "success")
    except Exception as e:
        logger.error("Pipeline %s failed: %s", batch_id, e)
        await release_pipeline_lock(run_id, "failed", str(e))
        raise

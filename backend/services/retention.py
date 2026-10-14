"""Retention for pipeline debug data.

`pipeline_checkpoints` held 73% of the database (181 MB of 248 MB, 2026-10-14)
because every daily run stores full collect/enrich payloads and nothing pruned
them. Checkpoints are only needed for near-term reruns and A/B replays, so old
rows are deleted. `pipeline_logs` rows stay for analytics; only the bulky
`debug_meta` JSON is cleared after a longer window.
"""
import logging
from datetime import datetime, timedelta, timezone

from postgrest.types import CountMethod, ReturnMethod

logger = logging.getLogger(__name__)

CHECKPOINT_RETENTION_DAYS = 14
DEBUG_META_RETENTION_DAYS = 60


def _cutoff(now: datetime, days: int) -> str:
    start_of_day = now.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return (start_of_day - timedelta(days=days)).isoformat()


def prune_pipeline_debug_data(supabase, now: datetime | None = None) -> dict:
    """Delete old checkpoints and clear old log debug_meta. Never raises."""
    # returning=minimal: the default returns every deleted row, which would
    # download the whole checkpoint payload and burn the egress we are saving.
    now = now or datetime.now(timezone.utc)
    result = {"checkpoints_deleted": 0, "debug_meta_cleared": 0, "errors": []}

    try:
        deleted = (
            supabase.table("pipeline_checkpoints")
            .delete(count=CountMethod.exact, returning=ReturnMethod.minimal)
            .lt("created_at", _cutoff(now, CHECKPOINT_RETENTION_DAYS))
            .execute()
        )
        result["checkpoints_deleted"] = deleted.count or 0
    except Exception as e:
        result["errors"].append(f"pipeline_checkpoints: {e}")

    try:
        cleared = (
            supabase.table("pipeline_logs")
            .update({"debug_meta": None}, count=CountMethod.exact, returning=ReturnMethod.minimal)
            .lt("created_at", _cutoff(now, DEBUG_META_RETENTION_DAYS))
            .not_.is_("debug_meta", "null")
            .execute()
        )
        result["debug_meta_cleared"] = cleared.count or 0
    except Exception as e:
        result["errors"].append(f"pipeline_logs: {e}")

    if result["errors"]:
        logger.warning("Retention prune errors: %s", result["errors"])
    logger.info(
        "Retention prune: %d checkpoints deleted, %d debug_meta cleared",
        result["checkpoints_deleted"], result["debug_meta_cleared"],
    )
    return result

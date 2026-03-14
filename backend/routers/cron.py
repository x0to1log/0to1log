"""Cron-triggered pipeline endpoints."""
import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends

from core.security import verify_cron_secret
from services.pipeline import run_daily_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cron", tags=["cron"])


@router.post("/news-pipeline", status_code=202)
async def trigger_news_pipeline(
    background_tasks: BackgroundTasks,
    _secret=Depends(verify_cron_secret),
):
    """Trigger the daily AI news pipeline. Returns 202 immediately."""
    batch_id = date.today().isoformat()

    async def _run():
        try:
            result = await run_daily_pipeline(batch_id=batch_id)
            logger.info(
                "Pipeline batch %s finished: %d posts, %d errors",
                result.batch_id, result.posts_created, len(result.errors),
            )
        except Exception as e:
            logger.error("Pipeline batch %s crashed: %s", batch_id, e)

    background_tasks.add_task(_run)

    return {
        "status": "accepted",
        "batch_id": batch_id,
        "message": "Pipeline started in background",
    }


@router.get("/health")
async def cron_health():
    """Health check for cron service."""
    return {
        "status": "ok",
        "pipeline": "news-v2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

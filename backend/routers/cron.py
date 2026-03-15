"""Cron-triggered pipeline endpoints."""
import logging
import re
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from core.security import verify_cron_secret
from services.pipeline import run_daily_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cron", tags=["cron"])

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class PipelineTriggerBody(BaseModel):
    mode: str = "resume"
    target_date: Optional[str] = None


@router.post("/news-pipeline", status_code=202)
async def trigger_news_pipeline(
    background_tasks: BackgroundTasks,
    body: PipelineTriggerBody | None = None,
    _secret=Depends(verify_cron_secret),
):
    """Trigger the daily AI news pipeline. Returns 202 immediately."""
    target_date = body.target_date if body else None

    if target_date:
        if not _DATE_RE.match(target_date):
            raise HTTPException(400, "target_date must be YYYY-MM-DD")
        try:
            td = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(400, "Invalid date")
        if td > date.today():
            raise HTTPException(400, "target_date cannot be in the future")

    batch_id = target_date or date.today().isoformat()

    async def _run():
        try:
            result = await run_daily_pipeline(
                batch_id=batch_id, target_date=target_date,
            )
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

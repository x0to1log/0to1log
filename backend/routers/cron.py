import asyncio
import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request

from core.rate_limit import limiter
from core.security import verify_cron_secret
from models.posts import PipelineAcceptedResponse, ErrorResponse
from services.pipeline import run_daily_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cron"])


@router.post(
    "/cron/news-pipeline",
    status_code=202,
    response_model=PipelineAcceptedResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid cron secret"},
    },
)
@limiter.limit("5/minute")
async def run_news_pipeline(
    request: Request,
    background_tasks: BackgroundTasks,
    batch_id: Optional[str] = Query(
        None,
        description="Custom batch ID (e.g. 2026-03-05). Defaults to today.",
    ),
    _: None = Depends(verify_cron_secret),
):
    """Trigger daily news pipeline. Returns 202 immediately; runs async."""
    resolved_batch = batch_id or date.today().isoformat()
    background_tasks.add_task(run_daily_pipeline, resolved_batch)
    return PipelineAcceptedResponse(
        accepted=True,
        message=f"Pipeline queued for batch {resolved_batch}",
    )


async def _run_backfill(start: date, end: date) -> None:
    """Run pipelines for a date range sequentially."""
    current = start
    while current <= end:
        batch_id = current.isoformat()
        logger.info("Backfill: starting batch %s", batch_id)
        try:
            await run_daily_pipeline(batch_id)
        except Exception as e:
            logger.error("Backfill: batch %s failed: %s", batch_id, e)
        # Small delay between batches to avoid rate limits
        await asyncio.sleep(2)
        current += timedelta(days=1)
    logger.info("Backfill complete: %s to %s", start.isoformat(), end.isoformat())


@router.post(
    "/cron/backfill",
    status_code=202,
    response_model=PipelineAcceptedResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid cron secret"},
    },
)
@limiter.limit("2/minute")
async def backfill_pipeline(
    request: Request,
    background_tasks: BackgroundTasks,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    _: None = Depends(verify_cron_secret),
):
    """Backfill pipeline for a date range. Runs sequentially in background."""
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    days = (end - start).days + 1

    if days < 1 or days > 30:
        return PipelineAcceptedResponse(
            accepted=False,
            message="Date range must be 1-30 days.",
        )

    background_tasks.add_task(_run_backfill, start, end)
    return PipelineAcceptedResponse(
        accepted=True,
        message=f"Backfill queued for {days} days: {start_date} to {end_date}",
    )

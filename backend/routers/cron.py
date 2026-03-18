"""Cron-triggered pipeline endpoints."""
import logging
import re
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from core.database import get_supabase
from core.rate_limit import limiter
from core.security import verify_cron_secret
from services.pipeline import check_existing_batch, cleanup_existing_batch, run_daily_pipeline, run_handbook_extraction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cron", tags=["cron"])

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class PipelineTriggerBody(BaseModel):
    mode: str = "resume"
    target_date: Optional[str] = None
    force: bool = False
    skip_handbook: bool = False


class PipelineCancelBody(BaseModel):
    run_id: str


@router.post("/news-pipeline", status_code=202)
@limiter.limit("2/minute")
async def trigger_news_pipeline(
    request: Request,
    background_tasks: BackgroundTasks,
    body: PipelineTriggerBody | None = None,
    _secret=Depends(verify_cron_secret),
):
    """Trigger the daily AI news pipeline. Returns 202 immediately."""
    target_date = body.target_date if body else None
    force = body.force if body else False

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

    # Check for existing data
    existing = check_existing_batch(batch_id)
    if existing:
        if existing["published_count"] > 0:
            raise HTTPException(422, {
                "error": "published_protected",
                "batch_id": batch_id,
                "published_count": existing["published_count"],
                "message": (
                    f"Cannot overwrite: {existing['published_count']} published "
                    f"posts exist for {batch_id}."
                ),
            })
        if not force:
            raise HTTPException(409, {
                "error": "batch_exists",
                "batch_id": batch_id,
                "existing": existing,
                "message": (
                    f"Data already exists for {batch_id}. "
                    f"Use force=true to overwrite."
                ),
            })
        # force=True: clean up existing data
        try:
            cleanup = cleanup_existing_batch(batch_id)
            logger.info("Force cleanup for %s: %s", batch_id, cleanup)
        except ValueError as e:
            raise HTTPException(422, {"error": "published_protected", "message": str(e)})

    async def _run():
        try:
            skip_handbook = body.skip_handbook if body else False
            result = await run_daily_pipeline(
                batch_id=batch_id, target_date=target_date,
                skip_handbook=skip_handbook,
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


class HandbookExtractBody(BaseModel):
    batch_id: str


@router.post("/handbook-extract", status_code=202)
@limiter.limit("2/minute")
async def trigger_handbook_extraction(
    request: Request,
    background_tasks: BackgroundTasks,
    body: HandbookExtractBody,
    _secret=Depends(verify_cron_secret),
):
    """Trigger handbook term extraction from existing news posts. Returns 202 immediately."""
    batch_id = body.batch_id

    async def _run():
        try:
            result = await run_handbook_extraction(batch_id)
            logger.info(
                "Handbook extraction batch %s finished: %d errors",
                batch_id, len(result.errors),
            )
        except Exception as e:
            logger.error("Handbook extraction batch %s crashed: %s", batch_id, e)

    background_tasks.add_task(_run)

    return {
        "status": "accepted",
        "batch_id": batch_id,
        "message": "Handbook extraction started in background",
    }


@router.post("/pipeline-cancel", status_code=200)
@limiter.limit("5/minute")
async def cancel_pipeline_run(
    request: Request,
    body: PipelineCancelBody,
    _secret=Depends(verify_cron_secret),
):
    """Cancel a running pipeline by marking it as failed."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(500, "Supabase not configured")
    try:
        supabase.table("pipeline_runs").update({
            "status": "failed",
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "last_error": "Cancelled by admin",
        }).eq("id", body.run_id).eq("status", "running").execute()
    except Exception as e:
        logger.error("Pipeline cancel error: %s", e)
        raise HTTPException(500, "Failed to cancel pipeline")
    return {"status": "cancelled", "run_id": body.run_id}


@router.get("/health")
async def cron_health():
    """Health check for cron service."""
    return {
        "status": "ok",
        "pipeline": "news-v2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

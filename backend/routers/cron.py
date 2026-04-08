"""Cron-triggered pipeline endpoints."""
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from core.config import today_kst
from core.database import get_supabase
from core.rate_limit import limiter
from core.security import verify_cron_secret
from services.pipeline import check_existing_batch, cleanup_existing_batch, rerun_pipeline_stage, run_daily_pipeline, run_handbook_extraction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cron", tags=["cron"])

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class PipelineTriggerBody(BaseModel):
    mode: str = "resume"
    target_date: Optional[str] = None
    force: bool = False
    skip_handbook: bool = False
    is_cron: bool = False


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
        if td > datetime.strptime(today_kst(), "%Y-%m-%d").date():
            raise HTTPException(400, "target_date cannot be in the future")

    batch_id = target_date or today_kst()

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
            # If request explicitly says skip_handbook=true, respect it immediately.
            # Otherwise, ALWAYS check admin_settings to decide.
            skip_handbook = body.skip_handbook if body else False
            if not skip_handbook:
                try:
                    sb = get_supabase()
                    if sb:
                        row = sb.table("admin_settings").select("value").eq("key", "handbook_auto_extract").single().execute()
                        if row.data and row.data.get("value") is False:
                            skip_handbook = True
                            logger.info("Handbook extraction disabled via admin_settings")
                        else:
                            logger.info("Handbook extraction enabled (admin_settings value=%s)", row.data.get("value") if row.data else "missing")
                except Exception as e:
                    # Default to DISABLED if setting unavailable — safer than silently extracting
                    skip_handbook = True
                    logger.warning("Could not read handbook_auto_extract setting (%s), defaulting to SKIP", e)
            force_fresh = body.force if body else False
            is_cron = body.is_cron if body else False
            result = await run_daily_pipeline(
                batch_id=batch_id, target_date=target_date,
                skip_handbook=skip_handbook,
                force_fresh=force_fresh,
                auto_publish=is_cron,
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
        # Check admin setting before extraction
        try:
            sb = get_supabase()
            if sb:
                row = sb.table("admin_settings").select("value").eq("key", "handbook_auto_extract").single().execute()
                if row.data and row.data.get("value") is False:
                    logger.info("Handbook extraction SKIPPED for batch %s — disabled via admin_settings", batch_id)
                    return
        except Exception as e:
            # Default to SKIP if setting unavailable
            logger.warning("Could not read handbook_auto_extract setting (%s), skipping extraction", e)
            return

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


class WeeklyTriggerBody(BaseModel):
    week_id: str | None = None


@router.post("/weekly", status_code=202)
@limiter.limit("2/minute")
async def trigger_weekly_pipeline(
    request: Request,
    background_tasks: BackgroundTasks,
    body: WeeklyTriggerBody | None = None,
    _secret=Depends(verify_cron_secret),
):
    """Trigger weekly recap generation. Returns 202 immediately."""
    week_id = (body.week_id if body else None)

    async def _run():
        try:
            from services.pipeline import run_weekly_pipeline
            result = await run_weekly_pipeline(week_id=week_id)
            logger.info(
                "Weekly pipeline %s finished: %d posts, %d errors",
                result.batch_id, result.posts_created, len(result.errors),
            )
        except Exception as e:
            logger.error("Weekly pipeline crashed: %s", e)

    background_tasks.add_task(_run)

    return {
        "status": "accepted",
        "week_id": week_id or "auto (previous week)",
        "message": "Weekly pipeline started in background",
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


class PipelineRerunBody(BaseModel):
    run_id: str
    from_stage: str  # "classify"|"merge"|"community"|"write"
    batch_id: str  # YYYY-MM-DD
    category: Optional[str] = None  # "research"|"business"|None


@router.post("/pipeline-rerun", status_code=202)
@limiter.limit("5/minute")
async def rerun_pipeline(
    request: Request,
    body: PipelineRerunBody,
    background_tasks: BackgroundTasks,
    _secret=Depends(verify_cron_secret),
):
    """Rerun pipeline from a specific stage using saved checkpoints."""
    valid_stages = {"classify", "merge", "community", "write"}
    if body.from_stage not in valid_stages:
        raise HTTPException(400, f"Invalid from_stage: {body.from_stage}. Must be one of {valid_stages}")
    if body.category and body.category not in ("research", "business"):
        raise HTTPException(400, "category must be 'research', 'business', or null")

    async def _run():
        try:
            result = await rerun_pipeline_stage(
                source_run_id=body.run_id,
                from_stage=body.from_stage,
                batch_id=body.batch_id,
                category=body.category,
            )
            logger.info(
                "Rerun %s from %s: %d posts, %d errors",
                body.batch_id, body.from_stage, result.posts_created, len(result.errors),
            )
        except Exception as e:
            logger.error("Rerun failed: %s", e)

    background_tasks.add_task(_run)
    return {
        "status": "accepted",
        "run_id": body.run_id,
        "from_stage": body.from_stage,
        "message": f"Rerun from {body.from_stage} started in background",
    }


@router.get("/health")
async def cron_health():
    """Health check for cron service."""
    return {
        "status": "ok",
        "pipeline": "news-v2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

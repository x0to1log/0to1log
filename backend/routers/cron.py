from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from core.rate_limit import limiter
from core.security import verify_cron_secret
from models.posts import PipelineAcceptedResponse, ErrorResponse
from services.pipeline import run_daily_pipeline

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
    _: None = Depends(verify_cron_secret),
):
    """Trigger daily news pipeline. Returns 202 immediately; runs async."""
    batch_id = date.today().isoformat()
    background_tasks.add_task(run_daily_pipeline, batch_id)
    return PipelineAcceptedResponse(
        accepted=True,
        message=f"Pipeline queued for batch {batch_id}",
    )

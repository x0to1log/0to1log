from fastapi import APIRouter, BackgroundTasks, Depends, Request

from core.security import verify_cron_secret
from models.posts import PipelineAcceptedResponse, ErrorResponse

router = APIRouter(tags=["cron"])


@router.post(
    "/cron/news-pipeline",
    status_code=202,
    response_model=PipelineAcceptedResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid cron secret"},
    },
)
async def run_news_pipeline(
    request: Request,
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_cron_secret),
):
    """Trigger daily news pipeline. Returns 202 immediately; runs async."""
    # TODO: wire up background_tasks.add_task in Phase 2B-CRON-00
    return PipelineAcceptedResponse(
        accepted=True,
        message="Pipeline queued (Phase 2A stub)",
    )

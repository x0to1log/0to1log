from fastapi import APIRouter, BackgroundTasks, Depends, Request

from core.security import verify_cron_secret

router = APIRouter(tags=["cron"])


@router.post("/cron/news-pipeline", status_code=202)
async def run_news_pipeline(
    request: Request,
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_cron_secret),
):
    """Trigger daily news pipeline. Returns 202 immediately; runs async."""
    # TODO: wire up pipeline orchestrator in Phase 2B
    # background_tasks.add_task(run_daily_pipeline, batch_id)

    return {"accepted": True, "message": "Pipeline queued (Phase 2A stub)"}

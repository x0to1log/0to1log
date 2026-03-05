from fastapi import APIRouter, BackgroundTasks, Header, HTTPException
from core.config import settings

router = APIRouter(tags=["cron"])


@router.post("/cron/news-pipeline", status_code=202)
async def run_news_pipeline(
    background_tasks: BackgroundTasks,
    x_cron_secret: str = Header(..., alias="x-cron-secret"),
):
    """Trigger daily news pipeline. Returns 202 immediately; runs async."""
    if x_cron_secret != settings.cron_secret:
        raise HTTPException(status_code=401, detail="Invalid cron secret")

    # TODO: implement pipeline in Phase 2
    # background_tasks.add_task(pipeline_orchestrator.run)

    return {"accepted": True, "message": "Pipeline queued (Phase 2 stub)"}

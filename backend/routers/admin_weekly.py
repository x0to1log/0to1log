"""Admin endpoints for weekly pipeline maintenance — per-persona regeneration."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from core.rate_limit import limiter
from core.security import require_admin
from services.pipeline import regenerate_weekly_persona

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/weekly", tags=["admin-weekly"])


class WeeklyRegenBody(BaseModel):
    week_id: str = Field(..., description="ISO week id, e.g. '2026-W16'")
    persona: str = Field(..., description="'expert' or 'learner'")


@router.post("/regenerate")
@limiter.limit("3/minute")
async def regenerate_persona(
    request: Request,
    body: WeeklyRegenBody,
    _user=Depends(require_admin),
):
    """Regenerate ONE persona of an existing weekly post.

    Synchronous — waits for the full regen (5-10 min). Uses the same LLM helper
    as run_weekly_pipeline so the generated content is identical in shape to a
    normal run, but only the specified persona's fields are overwritten on the
    existing news_posts rows.
    """
    try:
        return await regenerate_weekly_persona(body.week_id, body.persona)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.exception("Weekly regen endpoint error")
        raise HTTPException(status_code=500, detail=f"Regen failed: {e}")

"""Admin AI Advisor router — post actions + deep verify + handbook."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from openai import APITimeoutError, APIError

from core.rate_limit import limiter
from core.security import require_admin
from models.advisor import (
    AiAdviseRequest,
    AiAdviseResponse,
    HandbookAdviseRequest,
    HandbookAdviseResponse,
)
from services.agents.advisor import run_advise, run_deep_verify, run_handbook_advise

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/ai", tags=["admin-ai"])


@router.post("/advise", response_model=AiAdviseResponse)
@limiter.limit("5/minute")
async def advise(request: Request, body: AiAdviseRequest, _user=Depends(require_admin)):
    """Run an AI advisor action on the current post."""
    try:
        if body.action == "deepverify":
            result, model, tokens = await run_deep_verify(body)
        else:
            result, model, tokens = await run_advise(body)
    except APITimeoutError:
        raise HTTPException(status_code=504, detail="AI request timed out")
    except APIError as e:
        logger.error("OpenAI API error in advisor [%s]: %s", body.action, e)
        raise HTTPException(status_code=502, detail="AI service unavailable")
    except Exception as e:
        logger.error("Advisor [%s] unexpected error: %s", body.action, e)
        raise HTTPException(status_code=500, detail="AI returned invalid response")

    return AiAdviseResponse(
        action=body.action,
        success=True,
        result=result,
        model_used=model,
        tokens_used=tokens,
    )


@router.post("/handbook-advise", response_model=HandbookAdviseResponse)
@limiter.limit("5/minute")
async def handbook_advise(request: Request, body: HandbookAdviseRequest, _user=Depends(require_admin)):
    """Run an AI advisor action on a handbook term."""
    try:
        result, model, tokens, warnings = await run_handbook_advise(body)
    except APITimeoutError:
        raise HTTPException(status_code=504, detail="AI request timed out")
    except APIError as e:
        logger.error("OpenAI API error in handbook advisor [%s]: %s", body.action, e)
        raise HTTPException(status_code=502, detail="AI service unavailable")
    except Exception as e:
        logger.error("Handbook advisor [%s] unexpected error: %s", body.action, e)
        raise HTTPException(status_code=500, detail="AI returned invalid response")

    return HandbookAdviseResponse(
        action=body.action,
        success=not warnings,
        result=result,
        model_used=model,
        tokens_used=tokens,
        validation_warnings=warnings,
    )

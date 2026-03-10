"""Blog AI Advisor router — blog-specific advise + translate."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from openai import APITimeoutError, APIError

from core.rate_limit import limiter
from core.security import require_admin
from models.blog_advisor import (
    BlogAdviseRequest,
    BlogAdviseResponse,
    BlogTranslateRequest,
    BlogTranslateResponse,
)
from services.agents.blog_advisor import run_blog_advise, run_blog_translate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/blog-ai", tags=["admin-blog-ai"])


@router.post("/advise", response_model=BlogAdviseResponse)
@limiter.limit("5/minute")
async def blog_advise(request: Request, body: BlogAdviseRequest, _user=Depends(require_admin)):
    """Run a blog AI advisor action."""
    try:
        result, model, tokens = await run_blog_advise(body)
    except APITimeoutError:
        raise HTTPException(status_code=504, detail="AI request timed out")
    except APIError as e:
        logger.error("Blog AI error [%s]: %s", body.action, e)
        raise HTTPException(status_code=502, detail="AI service unavailable")
    except Exception as e:
        logger.error("Blog advisor [%s] unexpected error: %s", body.action, e)
        raise HTTPException(status_code=500, detail="AI returned invalid response")

    return BlogAdviseResponse(
        action=body.action,
        success=True,
        result=result,
        model_used=model,
        tokens_used=tokens,
    )


@router.post("/translate", response_model=BlogTranslateResponse)
@limiter.limit("3/minute")
async def blog_translate(request: Request, body: BlogTranslateRequest, _user=Depends(require_admin)):
    """Translate a blog post and create a new row."""
    try:
        result, model, tokens = await run_blog_translate(body)
    except APITimeoutError:
        raise HTTPException(status_code=504, detail="AI request timed out")
    except APIError as e:
        logger.error("Blog translate error: %s", e)
        raise HTTPException(status_code=502, detail="AI service unavailable")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error("Blog translate unexpected error: %s", e)
        raise HTTPException(status_code=500, detail="Translation failed")

    # Handle "already exists" case
    if result.get("already_exists"):
        return BlogTranslateResponse(
            success=False,
            translated_post_id=result.get("existing_post_id", ""),
            translated_slug=result.get("existing_slug", ""),
            target_locale=result.get("target_locale", ""),
            translation_group_id="",
            model_used="",
            tokens_used=0,
        )

    return BlogTranslateResponse(
        success=True,
        translated_post_id=result["translated_post_id"],
        translated_slug=result["translated_slug"],
        target_locale=result["target_locale"],
        translation_group_id=result["translation_group_id"],
        model_used=model,
        tokens_used=tokens,
    )

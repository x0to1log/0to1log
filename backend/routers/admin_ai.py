"""Admin AI Advisor router — post actions + deep verify + handbook."""

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
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

# In-memory job store for async handbook generation
_handbook_jobs: dict[str, dict] = {}


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


@router.post("/handbook-advise")
@limiter.limit("5/minute")
async def handbook_advise(
    request: Request,
    body: HandbookAdviseRequest,
    background_tasks: BackgroundTasks,
    _user=Depends(require_admin),
):
    """Run an AI advisor action on a handbook term.

    For 'generate' action: returns 202 + job_id immediately, runs in background.
    For other actions (seo, review, etc.): runs synchronously as before.
    """
    if body.action == "generate":
        job_id = str(uuid.uuid4())
        _handbook_jobs[job_id] = {"status": "running", "result": None, "error": None}

        async def _run_generate():
            try:
                result, model, tokens, warnings = await run_handbook_advise(body)
                _handbook_jobs[job_id] = {
                    "status": "completed",
                    "result": {
                        "action": body.action,
                        "success": not warnings,
                        "result": result,
                        "model_used": model,
                        "tokens_used": tokens,
                        "validation_warnings": warnings,
                    },
                    "error": None,
                }
                # Auto-save to DB so results survive polling failures
                if result:
                    try:
                        from core.database import get_supabase
                        sb = get_supabase()
                        if sb:
                            # Fields safe to auto-save (skip internal metadata keys starting with _)
                            save_fields = {
                                "definition_ko", "definition_en",
                                "body_basic_ko", "body_basic_en",
                                "body_advanced_ko", "body_advanced_en",
                                "korean_name", "korean_full", "term_full",
                                "categories",
                            }
                            update_data = {k: v for k, v in result.items() if k in save_fields and v}
                            if update_data and body.term_id:
                                sb.table("handbook_terms").update(update_data).eq("id", body.term_id).execute()
                                logger.info("Auto-saved generate result to DB for term %s (%d fields)", body.term_id, len(update_data))
                            elif update_data and body.term:
                                # New term without ID — save by term name match
                                sb.table("handbook_terms").update(update_data).eq("term", body.term).execute()
                                logger.info("Auto-saved generate result by term name '%s' (%d fields)", body.term, len(update_data))
                    except Exception as save_err:
                        logger.warning("Auto-save to DB failed: %s", save_err)
            except Exception as e:
                logger.error("Handbook generate background failed: %s", e)
                _handbook_jobs[job_id] = {
                    "status": "failed",
                    "result": None,
                    "error": str(e),
                }

        background_tasks.add_task(_run_generate)
        return {"status": "accepted", "job_id": job_id}

    # Non-generate actions: run synchronously (fast enough)
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

    # Propagate search_sources from the result dict to the top-level
    # response field so the API contract in HandbookAdviseResponse is
    # actually populated. The service writes the list inside `result`;
    # we mirror it out here so API consumers can read either location.
    search_sources = result.get("search_sources", []) if isinstance(result, dict) else []

    return HandbookAdviseResponse(
        action=body.action,
        success=not warnings,
        result=result,
        model_used=model,
        tokens_used=tokens,
        search_sources=search_sources,
        validation_warnings=warnings,
    )


@router.get("/handbook-job/{job_id}")
async def handbook_job_status(job_id: str, _user=Depends(require_admin)):
    """Poll for handbook generate job status."""
    job = _handbook_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job

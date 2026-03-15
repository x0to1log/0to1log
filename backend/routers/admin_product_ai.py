"""Product AI Advisor router — generate taglines and descriptions for AI products."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from openai import APITimeoutError, APIError

from core.rate_limit import limiter
from core.security import require_admin
from models.product_advisor import ProductGenerateRequest, ProductGenerateResponse
from services.agents.product_advisor import run_product_generate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/product-ai", tags=["admin-product-ai"])


@router.post("/generate", response_model=ProductGenerateResponse)
@limiter.limit("5/minute")
async def product_generate(
    request: Request,
    body: ProductGenerateRequest,
    _user=Depends(require_admin),
):
    """Generate tagline or description for an AI product."""
    try:
        result, model, tokens = await run_product_generate(body)
    except APITimeoutError:
        raise HTTPException(status_code=504, detail="AI request timed out")
    except APIError as e:
        logger.error("Product AI error [%s]: %s", body.action, e)
        raise HTTPException(status_code=502, detail="AI service unavailable")
    except Exception as e:
        logger.error("Product advisor [%s] unexpected error: %s", body.action, e)
        raise HTTPException(status_code=500, detail="AI returned invalid response")

    return ProductGenerateResponse(
        action=body.action,
        success=True,
        result=result,
        model_used=model,
        tokens_used=tokens,
    )

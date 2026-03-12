import json
import logging
import re
from decimal import Decimal
from typing import Any

from openai import AsyncOpenAI

from core.config import settings

logger = logging.getLogger(__name__)
OPENAI_MODEL_PRICING_PER_1M = {
    "gpt-4o": {"input": Decimal("2.50"), "output": Decimal("10.00")},
    "gpt-4o-mini": {"input": Decimal("0.15"), "output": Decimal("0.60")},
}


def get_openai_client() -> AsyncOpenAI:
    """Return a configured AsyncOpenAI client with 120s timeout."""
    return AsyncOpenAI(api_key=settings.openai_api_key, timeout=120.0)


def _resolve_pricing_key(model_name: str | None) -> str | None:
    if not model_name:
        return None

    if model_name in OPENAI_MODEL_PRICING_PER_1M:
        return model_name

    for candidate in OPENAI_MODEL_PRICING_PER_1M:
        if model_name.startswith(candidate):
            return candidate

    return None


def estimate_openai_cost_usd(
    model_name: str | None,
    input_tokens: int,
    output_tokens: int,
) -> float | None:
    pricing_key = _resolve_pricing_key(model_name)
    if not pricing_key:
        return None

    pricing = OPENAI_MODEL_PRICING_PER_1M[pricing_key]
    total = (
        (Decimal(input_tokens) * pricing["input"])
        + (Decimal(output_tokens) * pricing["output"])
    ) / Decimal(1_000_000)
    return float(total)


def extract_usage_metrics(response: Any, model_name: str | None) -> dict[str, Any]:
    usage = getattr(response, "usage", None)
    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    total_tokens_raw = getattr(usage, "total_tokens", None)
    total_tokens = (
        int(total_tokens_raw)
        if total_tokens_raw is not None
        else prompt_tokens + completion_tokens
    )

    return {
        "model_used": model_name,
        "input_tokens": prompt_tokens,
        "output_tokens": completion_tokens,
        "tokens_used": total_tokens,
        "cost_usd": estimate_openai_cost_usd(model_name, prompt_tokens, completion_tokens),
    }


def merge_usage_metrics(
    left: dict[str, Any] | None,
    right: dict[str, Any] | None,
) -> dict[str, Any]:
    left = left or {}
    right = right or {}

    left_cost = left.get("cost_usd")
    right_cost = right.get("cost_usd")
    merged_cost: float | None
    if left_cost is None and right_cost is None:
        merged_cost = None
    else:
        merged_cost = float((Decimal(str(left_cost or 0)) + Decimal(str(right_cost or 0))))

    left_model = left.get("model_used")
    right_model = right.get("model_used")
    if left_model and right_model and left_model != right_model:
        merged_model = "multiple"
    else:
        merged_model = right_model or left_model

    return {
        "model_used": merged_model,
        "input_tokens": int(left.get("input_tokens", 0) or 0) + int(right.get("input_tokens", 0) or 0),
        "output_tokens": int(left.get("output_tokens", 0) or 0) + int(right.get("output_tokens", 0) or 0),
        "tokens_used": int(left.get("tokens_used", 0) or 0) + int(right.get("tokens_used", 0) or 0),
        "cost_usd": merged_cost,
    }


def parse_ai_json(raw: str, agent_name: str) -> dict:
    """Parse AI response as JSON with fallback for code-block wrapping."""
    logger.info("%s raw response (first 500 chars): %.500s", agent_name, raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        logger.error("%s: failed to parse JSON: %.1000s", agent_name, raw)
        raise

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
    "gpt-4.1": {"input": Decimal("2.00"), "output": Decimal("8.00")},
    "gpt-4.1-mini": {"input": Decimal("0.40"), "output": Decimal("1.60")},
    "gpt-4.1-nano": {"input": Decimal("0.10"), "output": Decimal("0.40")},
    "gpt-5": {"input": Decimal("2.00"), "output": Decimal("8.00")},
    "gpt-5-mini": {"input": Decimal("0.25"), "output": Decimal("2.00")},
    "gpt-5-nano": {"input": Decimal("0.05"), "output": Decimal("0.40")},
    "o4-mini": {"input": Decimal("1.10"), "output": Decimal("4.40")},
    "o3": {"input": Decimal("2.00"), "output": Decimal("8.00")},
    "o3-mini": {"input": Decimal("1.10"), "output": Decimal("4.40")},
}


def get_openai_client() -> AsyncOpenAI:
    """Return a configured AsyncOpenAI client."""
    return AsyncOpenAI(api_key=settings.openai_api_key, timeout=300.0)


def is_o_series(model: str) -> bool:
    """Check if model is an o-series reasoning model (o1, o3, o4-mini, etc.)."""
    return model.startswith("o1") or model.startswith("o3") or model.startswith("o4")


def _uses_max_completion_tokens(model: str) -> bool:
    """Models that require max_completion_tokens instead of max_tokens."""
    return is_o_series(model) or model.startswith("gpt-5")


def _apply_gpt5_compat(kwargs: dict, model: str) -> dict:
    """Apply gpt-5/o-series compatibility to kwargs.

    gpt-5 is a reasoning model — reasoning tokens consume max_completion_tokens.
    Without enough headroom, reasoning uses all tokens and output is empty.
    Fix: multiply token budget by 3x and set reasoning_effort=low.
    """
    # max_tokens → max_completion_tokens (with 3x headroom for reasoning)
    if _uses_max_completion_tokens(model) and "max_tokens" in kwargs:
        original = kwargs.pop("max_tokens")
        kwargs["max_completion_tokens"] = original * 3
    elif _uses_max_completion_tokens(model) and "max_completion_tokens" in kwargs:
        kwargs["max_completion_tokens"] = kwargs["max_completion_tokens"] * 3

    # gpt-5 and o-series don't support temperature
    if is_o_series(model) or model.startswith("gpt-5"):
        kwargs.pop("temperature", None)

    # gpt-5: reduce reasoning effort to save tokens for actual output
    if model.startswith("gpt-5") and "reasoning_effort" not in kwargs:
        kwargs["reasoning_effort"] = "low"

    return kwargs


def compat_create_kwargs(model: str, **kwargs) -> dict:
    """Make chat.completions.create kwargs compatible with gpt-5/o-series.

    Use for direct API calls that don't go through build_completion_kwargs.
    """
    kwargs["model"] = model
    return _apply_gpt5_compat(kwargs, model)


def build_completion_kwargs(
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float = 0.3,
    response_format: dict | None = None,
    reasoning_effort: str | None = None,
) -> dict:
    """Build kwargs for chat.completions.create, handling model differences."""
    kwargs: dict[str, Any] = {"model": model, "messages": messages}
    if _uses_max_completion_tokens(model):
        kwargs["max_completion_tokens"] = max_tokens
    else:
        kwargs["max_tokens"] = max_tokens
    kwargs["temperature"] = temperature
    if response_format:
        kwargs["response_format"] = response_format
    if reasoning_effort is not None:
        kwargs["reasoning_effort"] = reasoning_effort
    return _apply_gpt5_compat(kwargs, model)


def _resolve_pricing_key(model_name: str | None) -> str | None:
    if not model_name:
        return None

    if model_name in OPENAI_MODEL_PRICING_PER_1M:
        return model_name

    # Match longest key first to avoid e.g. "gpt-4o-mini" matching "gpt-4o"
    for candidate in sorted(OPENAI_MODEL_PRICING_PER_1M, key=len, reverse=True):
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

import asyncio
import json
import logging
import re
from decimal import Decimal
from typing import Any, Awaitable, Callable, TypeVar

import openai
from openai import AsyncOpenAI

from core.config import settings

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


async def with_flex_retry(
    fn: Callable[[], Awaitable[_T]],
    *,
    max_attempts: int = 3,
    base_delay: float = 2.0,
) -> _T:
    """Retry an OpenAI call on 429 resource-unavailable (flex-tier capacity).

    Exponential backoff: base_delay, 2*base_delay, 4*base_delay, ... Only
    retries openai.RateLimitError; every other exception (BadRequestError
    from strict-schema validation, timeouts, auth errors) passes through
    unchanged. Per OpenAI flex docs, 429 on flex tier is not charged, so
    retrying is free.
    """
    for attempt in range(max_attempts):
        try:
            return await fn()
        except openai.RateLimitError as e:
            if attempt == max_attempts - 1:
                raise
            delay = base_delay * (2 ** attempt)
            logger.warning(
                "flex 429 (attempt %d/%d) — backing off %.1fs: %s",
                attempt + 1, max_attempts, delay, e,
            )
            await asyncio.sleep(delay)
    # Unreachable — the final attempt either returns or re-raises
    raise RuntimeError("with_flex_retry: loop exited without returning or raising")
OPENAI_MODEL_PRICING_PER_1M = {
    "gpt-5": {"input": Decimal("2.00"), "output": Decimal("8.00")},
    "gpt-5-mini": {"input": Decimal("0.25"), "output": Decimal("2.00")},
    "gpt-5-nano": {"input": Decimal("0.05"), "output": Decimal("0.40")},
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
    """Apply gpt-5 compatibility: 3x token headroom for reasoning + low default effort.

    Two token paths to handle:
    1. compat_create_kwargs caller passed max_tokens → pop + rename + 3x.
    2. build_completion_kwargs caller already set max_completion_tokens → 3x in place.
    """
    if _uses_max_completion_tokens(model) and "max_tokens" in kwargs:
        original = kwargs.pop("max_tokens")
        kwargs["max_completion_tokens"] = original * 3
    elif _uses_max_completion_tokens(model) and "max_completion_tokens" in kwargs:
        kwargs["max_completion_tokens"] = kwargs["max_completion_tokens"] * 3

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
    response_format: dict | None = None,
    reasoning_effort: str | None = None,
    service_tier: str | None = None,
    verbosity: str | None = None,
    prompt_cache_key: str | None = None,
) -> dict:
    """Build kwargs for chat.completions.create for gpt-5 family.

    Note: `temperature` is not accepted — gpt-5/o-series reject it at the API.
    If a non-reasoning model family is re-introduced, re-add the parameter here.
    """
    kwargs: dict[str, Any] = {"model": model, "messages": messages}
    kwargs["max_completion_tokens"] = max_tokens  # all production models are gpt-5 family
    if response_format:
        kwargs["response_format"] = response_format
    if reasoning_effort is not None:
        kwargs["reasoning_effort"] = reasoning_effort
    if service_tier is not None:
        kwargs["service_tier"] = service_tier
    if verbosity is not None:
        kwargs["verbosity"] = verbosity
    if prompt_cache_key is not None:
        kwargs["prompt_cache_key"] = prompt_cache_key
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
    cached_tokens: int = 0,
    service_tier: str | None = None,
) -> float | None:
    """Estimate cost of an OpenAI call, accounting for cache + service tier.

    Pricing rules:
    - Standard input: pricing["input"] per 1M tokens.
    - Cached input: 10% of standard input (OpenAI auto-discount, applied to
      tokens reported in response.usage.prompt_tokens_details.cached_tokens).
    - Standard output: pricing["output"] per 1M tokens.
    - service_tier="flex": 50% of standard rates on both input and output
      (Batch API rates). Discounts stack multiplicatively with cache.
    - service_tier in {None, "auto", "default", "priority", "scale"} or
      anything else: full standard rate. "priority" is actually a premium
      tier but we don't track the uplift — treat as standard for now.

    Returns None if the model isn't in the pricing table.
    """
    pricing_key = _resolve_pricing_key(model_name)
    if not pricing_key:
        return None

    pricing = OPENAI_MODEL_PRICING_PER_1M[pricing_key]
    tier_multiplier = Decimal("0.5") if service_tier == "flex" else Decimal("1.0")
    cached = max(0, int(cached_tokens or 0))
    fresh_input = max(0, int(input_tokens) - cached)

    fresh_input_cost = Decimal(fresh_input) * pricing["input"] * tier_multiplier
    cached_input_cost = Decimal(cached) * pricing["input"] * Decimal("0.1") * tier_multiplier
    output_cost = Decimal(int(output_tokens)) * pricing["output"] * tier_multiplier

    total = (fresh_input_cost + cached_input_cost + output_cost) / Decimal(1_000_000)
    return float(total)


def extract_usage_metrics(response: Any, model_name: str | None) -> dict[str, Any]:
    """Extract tokens + cost from an OpenAI chat-completions response.

    Auto-detects ``response.service_tier`` (echoed back by the API — shows
    which tier actually served the request, not just what was requested)
    and feeds it into the cost estimate along with cached_tokens. Returns
    a dict with input_tokens, output_tokens, cached_tokens, tokens_used,
    cost_usd, model_used, service_tier.
    """
    usage = getattr(response, "usage", None)
    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    total_tokens_raw = getattr(usage, "total_tokens", None)
    total_tokens = (
        int(total_tokens_raw)
        if total_tokens_raw is not None
        else prompt_tokens + completion_tokens
    )

    details = getattr(usage, "prompt_tokens_details", None)
    cached_tokens = int(getattr(details, "cached_tokens", 0) or 0)

    # response.service_tier is the tier that actually served the request.
    # May be absent in older SDK mocks → treat as unknown → standard rate.
    service_tier = getattr(response, "service_tier", None)

    return {
        "model_used": model_name,
        "input_tokens": prompt_tokens,
        "output_tokens": completion_tokens,
        "cached_tokens": cached_tokens,
        "tokens_used": total_tokens,
        "service_tier": service_tier,
        "cost_usd": estimate_openai_cost_usd(
            model_name,
            prompt_tokens,
            completion_tokens,
            cached_tokens=cached_tokens,
            service_tier=service_tier,
        ),
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
        "cached_tokens": int(left.get("cached_tokens", 0) or 0) + int(right.get("cached_tokens", 0) or 0),
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

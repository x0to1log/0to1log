"""Tests for services.agents.client kwargs builder + flex retry."""
from unittest.mock import AsyncMock, MagicMock

import openai
import pytest

from services.agents.client import (
    _apply_gpt5_kwargs,
    build_completion_kwargs,
    with_flex_retry,
)


def _fake_rate_limit_error(msg: str = "resource unavailable") -> openai.RateLimitError:
    """Build a RateLimitError without hitting the real API.

    The SDK constructor requires an httpx.Response-like object, so we use
    MagicMock (which auto-provides any attribute access including .request).
    """
    return openai.RateLimitError(
        message=msg,
        response=MagicMock(status_code=429),
        body={"error": {"type": "requests"}},
    )


def test_gpt5_default_reasoning_effort_is_low():
    kwargs = {"model": "gpt-5", "max_tokens": 1000}
    out = _apply_gpt5_kwargs(kwargs, "gpt-5")
    assert out["reasoning_effort"] == "low"
    assert out["max_completion_tokens"] == 3000


def test_gpt5_caller_can_override_reasoning_effort_to_high():
    kwargs = {"model": "gpt-5", "max_tokens": 1000, "reasoning_effort": "high"}
    out = _apply_gpt5_kwargs(kwargs, "gpt-5")
    assert out["reasoning_effort"] == "high"


def test_build_completion_kwargs_passes_reasoning_effort_to_gpt5():
    out = build_completion_kwargs(
        model="gpt-5",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=1000,
        reasoning_effort="high",
    )
    assert out["reasoning_effort"] == "high"


def test_build_completion_kwargs_defaults_reasoning_effort_on_gpt5():
    out = build_completion_kwargs(
        model="gpt-5",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=1000,
    )
    # Still gets the default "low" injected by _apply_gpt5_kwargs
    assert out["reasoning_effort"] == "low"


@pytest.mark.asyncio
async def test_with_flex_retry_succeeds_after_one_429():
    """First call 429s, second succeeds — returns the success response."""
    mock_ok = MagicMock(choices=[MagicMock()])
    fn = AsyncMock(side_effect=[_fake_rate_limit_error(), mock_ok])
    out = await with_flex_retry(fn, max_attempts=3, base_delay=0.01)
    assert out is mock_ok
    assert fn.call_count == 2


@pytest.mark.asyncio
async def test_with_flex_retry_gives_up_after_max_attempts():
    err = _fake_rate_limit_error()
    fn = AsyncMock(side_effect=[err, err, err])
    with pytest.raises(openai.RateLimitError):
        await with_flex_retry(fn, max_attempts=3, base_delay=0.01)
    assert fn.call_count == 3


@pytest.mark.asyncio
async def test_with_flex_retry_passes_through_non_rate_limit_errors():
    """BadRequestError (strict-schema reject) must NOT be retried."""
    bad_req = openai.BadRequestError(
        message="schema invalid",
        response=MagicMock(status_code=400),
        body={"error": {"type": "invalid_request"}},
    )
    fn = AsyncMock(side_effect=[bad_req])
    with pytest.raises(openai.BadRequestError):
        await with_flex_retry(fn, max_attempts=3, base_delay=0.01)
    assert fn.call_count == 1


@pytest.mark.asyncio
async def test_with_flex_retry_succeeds_on_first_try():
    mock_ok = MagicMock()
    fn = AsyncMock(return_value=mock_ok)
    out = await with_flex_retry(fn, max_attempts=3, base_delay=0.01)
    assert out is mock_ok
    assert fn.call_count == 1


def _fake_5xx_error(status: int, msg: str = "upstream bad gateway") -> openai.APIStatusError:
    """Build an APIStatusError (parent of RateLimitError, BadRequestError, etc.).

    Simulates Cloudflare 502 / OpenAI 503 transient upstream errors —
    these were the cause of Apr 24 news pipeline failure.
    """
    return openai.APIStatusError(
        message=msg,
        response=MagicMock(status_code=status),
        body={"error": {"type": "origin_error"}},
    )


@pytest.mark.asyncio
async def test_with_flex_retry_succeeds_after_one_502():
    """Cloudflare 502 Bad Gateway — retry after backoff."""
    mock_ok = MagicMock()
    fn = AsyncMock(side_effect=[_fake_5xx_error(502), mock_ok])
    out = await with_flex_retry(fn, max_attempts=3, base_delay=0.01)
    assert out is mock_ok
    assert fn.call_count == 2


@pytest.mark.asyncio
async def test_with_flex_retry_succeeds_after_503_and_504():
    """Multiple transient 5xx recover with retries."""
    mock_ok = MagicMock()
    fn = AsyncMock(side_effect=[_fake_5xx_error(503), _fake_5xx_error(504), mock_ok])
    out = await with_flex_retry(fn, max_attempts=3, base_delay=0.01)
    assert out is mock_ok
    assert fn.call_count == 3


@pytest.mark.asyncio
async def test_with_flex_retry_gives_up_after_3_5xx_failures():
    err = _fake_5xx_error(502)
    fn = AsyncMock(side_effect=[err, err, err])
    with pytest.raises(openai.APIStatusError):
        await with_flex_retry(fn, max_attempts=3, base_delay=0.01)
    assert fn.call_count == 3


@pytest.mark.asyncio
async def test_with_flex_retry_does_not_retry_4xx():
    """Non-rate-limit 4xx (403, 404) should pass through — client-side errors."""
    err_403 = openai.APIStatusError(
        message="forbidden",
        response=MagicMock(status_code=403),
        body={"error": {"type": "authentication"}},
    )
    fn = AsyncMock(side_effect=[err_403])
    with pytest.raises(openai.APIStatusError):
        await with_flex_retry(fn, max_attempts=3, base_delay=0.01)
    assert fn.call_count == 1  # no retry


def test_build_completion_kwargs_passes_prompt_cache_key():
    out = build_completion_kwargs(
        model="gpt-5",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=1000,
        prompt_cache_key="digest-research-expert",
    )
    assert out["prompt_cache_key"] == "digest-research-expert"


def test_build_completion_kwargs_omits_prompt_cache_key_when_none():
    out = build_completion_kwargs(
        model="gpt-5",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=1000,
    )
    assert "prompt_cache_key" not in out


def test_build_completion_kwargs_passes_service_tier_and_cache_key_together():
    out = build_completion_kwargs(
        model="gpt-5",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=1000,
        service_tier="flex",
        prompt_cache_key="digest-business-learner",
    )
    assert out["service_tier"] == "flex"
    assert out["prompt_cache_key"] == "digest-business-learner"

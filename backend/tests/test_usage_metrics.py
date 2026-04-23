from types import SimpleNamespace

from services.agents.client import (
    build_completion_kwargs,
    estimate_openai_cost_usd,
    extract_usage_metrics,
    merge_usage_metrics,
)


def _resp(
    prompt: int,
    completion: int,
    cached: int | None,
    service_tier: str | None = None,
    reasoning: int | None = None,
) -> SimpleNamespace:
    details = None
    if cached is not None:
        details = SimpleNamespace(cached_tokens=cached)
    completion_details = None
    if reasoning is not None:
        completion_details = SimpleNamespace(reasoning_tokens=reasoning)
    usage_kwargs: dict = {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
        "prompt_tokens_details": details,
    }
    if completion_details is not None:
        usage_kwargs["completion_tokens_details"] = completion_details
    usage = SimpleNamespace(**usage_kwargs)
    # Only attach service_tier attribute if provided — some older mocks
    # won't have it, and extract_usage_metrics must handle that.
    if service_tier is not None:
        return SimpleNamespace(usage=usage, service_tier=service_tier)
    return SimpleNamespace(usage=usage)


def test_extract_usage_metrics_reads_cached_tokens():
    metrics = extract_usage_metrics(_resp(1000, 500, cached=800), "gpt-5-mini")
    assert metrics["cached_tokens"] == 800


def test_extract_usage_metrics_cached_tokens_zero_when_no_details():
    metrics = extract_usage_metrics(_resp(1000, 500, cached=None), "gpt-5-mini")
    assert metrics["cached_tokens"] == 0


def test_extract_usage_metrics_cached_tokens_zero_when_field_missing():
    usage = SimpleNamespace(
        prompt_tokens=100, completion_tokens=50, total_tokens=150,
        prompt_tokens_details=SimpleNamespace(),
    )
    resp = SimpleNamespace(usage=usage)
    metrics = extract_usage_metrics(resp, "gpt-5")
    assert metrics["cached_tokens"] == 0


def test_extract_usage_metrics_reads_reasoning_tokens():
    metrics = extract_usage_metrics(
        _resp(1000, 500, cached=None, reasoning=200), "gpt-5"
    )
    assert metrics["reasoning_tokens"] == 200


def test_extract_usage_metrics_reasoning_tokens_zero_when_missing():
    metrics = extract_usage_metrics(_resp(1000, 500, cached=None), "gpt-5")
    assert metrics["reasoning_tokens"] == 0


def test_merge_usage_metrics_sums_reasoning_tokens():
    left = {"reasoning_tokens": 100, "input_tokens": 0, "output_tokens": 0}
    right = {"reasoning_tokens": 250, "input_tokens": 0, "output_tokens": 0}
    merged = merge_usage_metrics(left, right)
    assert merged["reasoning_tokens"] == 350


def test_merge_usage_metrics_sums_cached_tokens():
    left = {"input_tokens": 100, "output_tokens": 50, "tokens_used": 150,
            "cached_tokens": 64, "cost_usd": 0.001, "model_used": "gpt-5-mini"}
    right = {"input_tokens": 200, "output_tokens": 100, "tokens_used": 300,
             "cached_tokens": 128, "cost_usd": 0.002, "model_used": "gpt-5-mini"}
    merged = merge_usage_metrics(left, right)
    assert merged["input_tokens"] == 300
    assert merged["output_tokens"] == 150
    assert merged["cached_tokens"] == 192


def test_build_completion_kwargs_forwards_service_tier():
    kwargs = build_completion_kwargs(
        "gpt-5-mini",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=100,
        service_tier="flex",
    )
    assert kwargs["service_tier"] == "flex"


def test_build_completion_kwargs_omits_service_tier_when_none():
    kwargs = build_completion_kwargs(
        "gpt-5-mini",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=100,
    )
    assert "service_tier" not in kwargs


def test_build_completion_kwargs_forwards_verbosity():
    kwargs = build_completion_kwargs(
        "gpt-5-mini",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=100,
        verbosity="low",
    )
    assert kwargs["verbosity"] == "low"


def test_build_completion_kwargs_omits_verbosity_when_none():
    kwargs = build_completion_kwargs(
        "gpt-5-mini",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=100,
    )
    assert "verbosity" not in kwargs


# ---------------------------------------------------------------------------
# Cost accounting — cached tokens + service_tier awareness
# ---------------------------------------------------------------------------

def _close(a: float | None, b: float, tol: float = 1e-9) -> bool:
    return a is not None and abs(a - b) < tol


def test_cost_standard_without_cached_tokens():
    # gpt-5: input $2/M, output $8/M
    # 1M input + 1M output = $2 + $8 = $10
    cost = estimate_openai_cost_usd("gpt-5", 1_000_000, 1_000_000)
    assert _close(cost, 10.0)


def test_cost_cached_tokens_billed_at_10_percent_of_input():
    # gpt-5: input $2/M. 1M input where 1M is cached:
    # cost = 1M * $2/M * 0.10 = $0.20
    cost = estimate_openai_cost_usd("gpt-5", 1_000_000, 0, cached_tokens=1_000_000)
    assert _close(cost, 0.20)


def test_cost_mixed_fresh_and_cached_input():
    # 1M input: 500K fresh + 500K cached, 0 output
    # fresh: 500K * $2/M = $1.00
    # cached: 500K * $2/M * 0.10 = $0.10
    # total = $1.10
    cost = estimate_openai_cost_usd("gpt-5", 1_000_000, 0, cached_tokens=500_000)
    assert _close(cost, 1.10)


def test_cost_flex_tier_halves_everything():
    # gpt-5: standard $10 for 1M in + 1M out; flex is 50% off = $5
    cost = estimate_openai_cost_usd(
        "gpt-5", 1_000_000, 1_000_000, service_tier="flex"
    )
    assert _close(cost, 5.0)


def test_cost_flex_and_cached_stack_multiplicatively():
    # 1M input all cached, 1M output, flex tier
    # input: 1M * $2 * 0.10 * 0.50 = $0.10
    # output: 1M * $8 * 0.50 = $4.00
    # total = $4.10
    cost = estimate_openai_cost_usd(
        "gpt-5", 1_000_000, 1_000_000,
        cached_tokens=1_000_000, service_tier="flex",
    )
    assert _close(cost, 4.10)


def test_cost_default_tier_treated_as_standard():
    # "default" or "auto" → full-rate
    cost = estimate_openai_cost_usd(
        "gpt-5", 1_000_000, 1_000_000, service_tier="default"
    )
    assert _close(cost, 10.0)


def test_cost_unknown_tier_treated_as_standard():
    cost = estimate_openai_cost_usd(
        "gpt-5", 1_000_000, 1_000_000, service_tier="scale"
    )
    assert _close(cost, 10.0)  # conservative default — don't assume discount


def test_cost_unknown_model_returns_none():
    assert estimate_openai_cost_usd("unknown-model", 100, 50) is None


# ---------------------------------------------------------------------------
# extract_usage_metrics auto-reads service_tier from response
# ---------------------------------------------------------------------------

def test_extract_usage_metrics_auto_reads_flex_tier():
    # gpt-5-mini: input $0.25/M, output $2/M → flex = $0.125 + $1 = $1.125 per 1M each
    metrics = extract_usage_metrics(
        _resp(1_000_000, 1_000_000, cached=None, service_tier="flex"),
        "gpt-5-mini",
    )
    # standard: 0.25 + 2.00 = 2.25; flex halves → 1.125
    assert _close(metrics["cost_usd"], 1.125)


def test_extract_usage_metrics_without_service_tier_attr_defaults_standard():
    # Older SDK mocks without .service_tier attr — must fall back to standard
    metrics = extract_usage_metrics(
        _resp(1_000_000, 1_000_000, cached=None),
        "gpt-5-mini",
    )
    assert _close(metrics["cost_usd"], 2.25)


def test_extract_usage_metrics_applies_cached_discount_end_to_end():
    # 1M input 90% cached, 0 output, standard tier
    # fresh = 100K * $0.25/M = $0.025
    # cached = 900K * $0.25/M * 0.10 = $0.0225
    # total = $0.0475
    metrics = extract_usage_metrics(
        _resp(1_000_000, 0, cached=900_000),
        "gpt-5-mini",
    )
    assert _close(metrics["cost_usd"], 0.0475)

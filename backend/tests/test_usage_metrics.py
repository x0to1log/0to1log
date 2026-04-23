from types import SimpleNamespace

from services.agents.client import build_completion_kwargs, extract_usage_metrics, merge_usage_metrics


def _resp(prompt: int, completion: int, cached: int | None) -> SimpleNamespace:
    details = None
    if cached is not None:
        details = SimpleNamespace(cached_tokens=cached)
    usage = SimpleNamespace(
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=prompt + completion,
        prompt_tokens_details=details,
    )
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


def test_build_completion_kwargs_omits_service_tier_for_non_gpt5():
    # service_tier should still pass through if user explicitly provides — that's the caller's problem
    # but for default None, never appear
    kwargs = build_completion_kwargs(
        "gpt-4.1-mini",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=100,
    )
    assert "service_tier" not in kwargs

"""Tests for services.agents.client gpt-5 compat + kwarg builder."""
from services.agents.client import _apply_gpt5_compat, build_completion_kwargs


def test_gpt5_default_reasoning_effort_is_low():
    kwargs = {"model": "gpt-5", "max_tokens": 1000, "temperature": 0.4}
    out = _apply_gpt5_compat(kwargs, "gpt-5")
    assert out["reasoning_effort"] == "low"
    assert "temperature" not in out
    assert out["max_completion_tokens"] == 3000


def test_gpt5_caller_can_override_reasoning_effort_to_high():
    kwargs = {"model": "gpt-5", "max_tokens": 1000, "reasoning_effort": "high"}
    out = _apply_gpt5_compat(kwargs, "gpt-5")
    assert out["reasoning_effort"] == "high"


def test_non_gpt5_model_untouched():
    kwargs = {"model": "gpt-4.1", "max_tokens": 1000, "temperature": 0.4}
    out = _apply_gpt5_compat(kwargs, "gpt-4.1")
    assert out["temperature"] == 0.4
    assert "reasoning_effort" not in out


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
    # Still gets the default "low" injected by _apply_gpt5_compat
    assert out["reasoning_effort"] == "low"

import pytest

from services.agents.advisor import ACTION_CONFIG


def test_review_action_has_flex_tier():
    """review action should be configured for flex tier."""
    assert ACTION_CONFIG["review"].get("service_tier") == "flex"


def test_review_action_has_prompt_cache_key():
    """review action should have a stable prompt_cache_key."""
    key = ACTION_CONFIG["review"].get("prompt_cache_key")
    assert key and key.startswith("advisor-")


@pytest.mark.parametrize("action", [
    "review", "factcheck", "conceptcheck", "voicecheck", "retrocheck",
])
def test_admin_check_actions_configured_for_flex_and_cache(action):
    cfg = ACTION_CONFIG[action]
    assert cfg["service_tier"] == "flex"
    assert cfg["prompt_cache_key"] == f"advisor-{action}"


def test_generate_and_seo_stay_on_standard_tier():
    """generate/seo are fast creative calls — keep on standard tier so
    the admin editor doesn't hit flex latency on 'Auto-generate'.
    """
    assert "service_tier" not in ACTION_CONFIG["generate"]
    assert "service_tier" not in ACTION_CONFIG["seo"]


def test_deep_verify_step1_uses_flex_and_cache_key():
    """run_deep_verify step1 (claim extraction) should route through flex
    with prompt_cache_key='advisor-deepverify-step1'. Verified by source
    inspection — the call site is a direct client.chat.completions.create,
    not dispatched through ACTION_CONFIG.
    """
    import inspect

    from services.agents import advisor

    src = inspect.getsource(advisor.run_deep_verify)
    assert 'prompt_cache_key="advisor-deepverify-step1"' in src
    assert 'service_tier="flex"' in src


def test_deep_verify_step2_uses_distinct_cache_key():
    """run_deep_verify step2 — same flex pattern with a distinct cache
    key since the system prompt (DEEPVERIFY_VERIFY_PROMPT) differs from
    step1's DEEPVERIFY_CLAIM_EXTRACT_PROMPT.
    """
    import inspect

    from services.agents import advisor

    src = inspect.getsource(advisor.run_deep_verify)
    assert 'prompt_cache_key="advisor-deepverify-step2"' in src

@pytest.mark.parametrize("cache_key", [
    "hb-generate-basic",
    "hb-generate-en-basic",
    "hb-generate-advanced",
    "hb-generate-en-advanced",
    "hb-regen-basic",
    "hb-regen-en-basic",
    "hb-regen-advanced",
    "hb-regen-en-advanced",
])
def test_handbook_writer_call_site_uses_flex(cache_key):
    """Every handbook writer/regen compat_create_kwargs call should pair
    reasoning_effort='high' + prompt_cache_key with service_tier='flex',
    matching the daily news writer pattern.

    Verified by source inspection — the call is far enough inside nested
    functions that mock-based verification would be brittle.
    """
    from pathlib import Path

    src = Path("services/agents/advisor.py").read_text(encoding="utf-8")
    # Find the block containing this cache_key literal
    marker = f'prompt_cache_key="{cache_key}"'
    idx = src.find(marker)
    assert idx != -1, f"cache_key {cache_key!r} not found in advisor.py"
    # Look at the surrounding lines for service_tier="flex"
    block_start = max(0, idx - 600)
    block_end = min(len(src), idx + 200)
    block = src[block_start:block_end]
    assert 'service_tier="flex"' in block, (
        f"{cache_key} call site is missing service_tier='flex'. "
        f"Expected within several lines of the prompt_cache_key literal."
    )


def test_log_handbook_stage_includes_reasoning_tokens():
    """_log_handbook_stage should record reasoning_tokens alongside
    cached_tokens and service_tier. extract_usage_metrics already returns it.
    Needed for Phase-2 reasoning_effort A/B measurement.
    """
    from pathlib import Path

    src = Path("services/agents/advisor.py").read_text(encoding="utf-8")
    marker = "def _log_handbook_stage("
    idx = src.find(marker)
    assert idx != -1
    body = src[idx:idx + 800]
    assert "reasoning_tokens" in body, (
        "_log_handbook_stage does not record reasoning_tokens — "
        "extract_usage_metrics returns it but it gets dropped."
    )


def test_log_advisor_call_helper_exists_and_is_callable():
    """advisor.py should expose _log_advisor_call(stage, usage, extra_meta)
    as a module-level helper for run_advise / run_deep_verify logging.
    """
    from services.agents import advisor

    assert hasattr(advisor, "_log_advisor_call")
    assert callable(advisor._log_advisor_call)


def test_log_advisor_call_writes_all_tier_and_token_fields():
    """When tier/cached/reasoning are present, they appear in debug_meta."""
    from unittest.mock import MagicMock, patch

    from services.agents import advisor

    fake_table = MagicMock()
    fake_supabase = MagicMock()
    fake_supabase.table.return_value = fake_table

    usage = {
        "model_used": "gpt-5-mini",
        "input_tokens": 1500,
        "output_tokens": 200,
        "cached_tokens": 1024,
        "reasoning_tokens": 140,
        "tokens_used": 1700,
        "cost_usd": 0.0008,
        "service_tier": "flex",
    }

    with patch("services.agents.advisor.get_supabase", return_value=fake_supabase):
        advisor._log_advisor_call("advisor.review", usage, extra_meta={"post_id": "abc"})

    fake_table.insert.assert_called_once()
    payload = fake_table.insert.call_args[0][0]
    assert payload["pipeline_type"] == "advisor.review"
    assert payload["tokens_used"] == 1700
    assert payload["cost_usd"] == 0.0008
    meta = payload["debug_meta"]
    assert meta["cached_tokens"] == 1024
    assert meta["reasoning_tokens"] == 140
    assert meta["service_tier"] == "flex"
    assert meta["post_id"] == "abc"


def test_log_advisor_call_handles_missing_supabase():
    """If get_supabase() returns None (test env without credentials),
    _log_advisor_call must no-op silently.
    """
    from unittest.mock import patch

    from services.agents import advisor

    usage = {"model_used": "gpt-5-mini", "input_tokens": 1, "output_tokens": 1,
             "tokens_used": 2, "cost_usd": 0.0}

    with patch("services.agents.advisor.get_supabase", return_value=None):
        # Should NOT raise
        advisor._log_advisor_call("advisor.review", usage)


def test_log_advisor_call_swallows_supabase_errors():
    """If the insert raises, _log_advisor_call must log-and-continue,
    not propagate — admin editor should never fail due to a logging bug.
    """
    from unittest.mock import MagicMock, patch

    from services.agents import advisor

    fake_table = MagicMock()
    fake_table.insert.side_effect = RuntimeError("db down")
    fake_supabase = MagicMock()
    fake_supabase.table.return_value = fake_table

    usage = {"model_used": "gpt-5-mini", "input_tokens": 1, "output_tokens": 1,
             "tokens_used": 2, "cost_usd": 0.0}

    with patch("services.agents.advisor.get_supabase", return_value=fake_supabase):
        # Should NOT raise
        advisor._log_advisor_call("advisor.review", usage)

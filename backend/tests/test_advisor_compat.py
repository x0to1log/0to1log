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

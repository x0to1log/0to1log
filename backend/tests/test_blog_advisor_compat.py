import pytest

from services.agents.blog_advisor import BLOG_ACTION_CONFIG


@pytest.mark.parametrize("action", ["review", "conceptcheck", "voicecheck", "retrocheck"])
def test_blog_check_actions_configured_for_flex_and_cache(action):
    cfg = BLOG_ACTION_CONFIG[action]
    assert cfg["service_tier"] == "flex"
    assert cfg["prompt_cache_key"] == f"blog-advisor-{action}"


def test_blog_creative_actions_stay_on_standard_tier():
    """outline/draft/rewrite/suggest/generate are interactive editor paths —
    keep on standard tier so 'Auto-draft' etc. don't hit flex latency.
    """
    for action in ("outline", "draft", "rewrite", "suggest", "generate"):
        assert "service_tier" not in BLOG_ACTION_CONFIG[action]


def test_blog_cache_keys_distinct_from_handbook_advisor():
    """Blog advisor uses 'blog-advisor-*' keys to avoid cache-slot collision
    with handbook advisor's 'advisor-*' keys (different system prompts would
    otherwise evict each other from the same cache slot).
    """
    for action in ("review", "conceptcheck", "voicecheck", "retrocheck"):
        key = BLOG_ACTION_CONFIG[action]["prompt_cache_key"]
        assert key.startswith("blog-advisor-")

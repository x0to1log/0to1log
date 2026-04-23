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


def test_log_blog_advisor_call_helper_exists():
    from services.agents import blog_advisor

    assert hasattr(blog_advisor, "_log_blog_advisor_call")
    assert callable(blog_advisor._log_blog_advisor_call)


def test_log_blog_advisor_call_writes_all_fields():
    """When tier/cached/reasoning are present, they appear in debug_meta."""
    from unittest.mock import MagicMock, patch

    from services.agents import blog_advisor

    fake_table = MagicMock()
    fake_supabase = MagicMock()
    fake_supabase.table.return_value = fake_table

    usage = {
        "model_used": "gpt-5-mini",
        "input_tokens": 1500,
        "output_tokens": 200,
        "cached_tokens": 512,
        "reasoning_tokens": 80,
        "tokens_used": 1700,
        "cost_usd": 0.0006,
        "service_tier": "flex",
    }

    with patch("services.agents.blog_advisor.get_supabase", return_value=fake_supabase):
        blog_advisor._log_blog_advisor_call(
            "blog-advisor.review", usage, extra_meta={"post_id": "blog-1"}
        )

    fake_table.insert.assert_called_once()
    payload = fake_table.insert.call_args[0][0]
    assert payload["pipeline_type"] == "blog-advisor.review"
    assert payload["tokens_used"] == 1700
    meta = payload["debug_meta"]
    assert meta["cached_tokens"] == 512
    assert meta["reasoning_tokens"] == 80
    assert meta["service_tier"] == "flex"
    assert meta["post_id"] == "blog-1"


def test_log_blog_advisor_call_handles_missing_supabase():
    from unittest.mock import patch

    from services.agents import blog_advisor

    usage = {"model_used": "gpt-5-mini", "input_tokens": 1, "output_tokens": 1,
             "tokens_used": 2, "cost_usd": 0.0}

    with patch("services.agents.blog_advisor.get_supabase", return_value=None):
        blog_advisor._log_blog_advisor_call("blog-advisor.review", usage)  # no raise


def test_log_blog_advisor_call_swallows_supabase_errors():
    from unittest.mock import MagicMock, patch

    from services.agents import blog_advisor

    fake_table = MagicMock()
    fake_table.insert.side_effect = RuntimeError("db down")
    fake_supabase = MagicMock()
    fake_supabase.table.return_value = fake_table

    usage = {"model_used": "gpt-5-mini", "input_tokens": 1, "output_tokens": 1,
             "tokens_used": 2, "cost_usd": 0.0}

    with patch("services.agents.blog_advisor.get_supabase", return_value=fake_supabase):
        blog_advisor._log_blog_advisor_call("blog-advisor.review", usage)  # no raise


@pytest.mark.asyncio
async def test_run_blog_advise_logs_to_pipeline_logs():
    from unittest.mock import AsyncMock, MagicMock, patch

    from services.agents import blog_advisor
    from models.blog_advisor import BlogAdviseRequest

    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content='{"score": 8, "comments": []}'))]
    mock_resp.usage = MagicMock(
        completion_tokens=42, prompt_tokens=100, total_tokens=142,
        prompt_tokens_details=MagicMock(cached_tokens=0),
        completion_tokens_details=MagicMock(reasoning_tokens=20),
    )
    mock_resp.service_tier = "flex"

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    req = BlogAdviseRequest(
        action="review", post_id="blog-1", title="t", content="c",
        category="engineering", locale="en",
    )

    with patch("services.agents.blog_advisor.get_openai_client", return_value=mock_client), \
         patch("services.agents.blog_advisor._log_blog_advisor_call") as mock_log:
        await blog_advisor.run_blog_advise(req)

    mock_log.assert_called_once()
    assert mock_log.call_args[0][0] == "blog-advisor.review"

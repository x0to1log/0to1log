"""Regression: _check_weekly_quality must pass usage= to _log_stage so
pipeline_logs.cost_usd is populated and admin pipeline-analytics can roll it
up. Also verifies stage name is `weekly:quality` (not `quality:weekly`) so
the dashboard's `pipeline_type LIKE 'weekly:%'` filter catches it.
"""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch


def _mock_qc_response(score: int = 80, prompt_tokens: int = 10000, completion_tokens: int = 2000):
    """Build a mocked OpenAI chat.completions response with valid rubric JSON."""
    rubric = {
        "total_score": score,
        "structural_completeness": {
            "sections_present": {"evidence": "7 sections", "score": 9},
            "section_depth": {"evidence": "depth adequate", "score": 8},
        },
        "source_quality": {
            "citation_coverage": {"evidence": "cited", "score": 8},
        },
        "issues": [],
    }
    msg = SimpleNamespace(content=json.dumps(rubric))
    choice = SimpleNamespace(message=msg)
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        prompt_tokens_details=SimpleNamespace(cached_tokens=0),
    )
    return SimpleNamespace(choices=[choice], usage=usage)


def _run_weekly_quality_with_mocks():
    """Call _check_weekly_quality with mocked OpenAI + captured _log_stage."""
    import services.pipeline  # noqa: F401 — resolve circular import before touching pipeline_quality
    from services.pipeline_quality import _check_weekly_quality

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=_mock_qc_response())

    log_stage_calls: list[dict] = []

    async def fake_log_stage(*args, **kwargs):
        log_stage_calls.append({"args": args, "kwargs": kwargs})

    supabase = MagicMock()

    with patch("services.pipeline_quality.get_openai_client", return_value=mock_client), \
         patch("services.pipeline_quality._log_stage", side_effect=fake_log_stage):
        asyncio.run(_check_weekly_quality(
            content_expert_en="English expert content. " * 500,
            content_learner_en="English learner content. " * 500,
            content_expert_ko="한국어 전문가 콘텐츠. " * 500,
            content_learner_ko="한국어 입문자 콘텐츠. " * 500,
            source_urls=[],
            supabase=supabase,
            run_id="test-run-1",
            cumulative_usage={},
        ))

    return log_stage_calls


def test_weekly_quality_success_log_uses_weekly_prefix():
    """Stage name must be `weekly:quality` so admin pipeline-analytics picks it up."""
    calls = _run_weekly_quality_with_mocks()
    success_calls = [c for c in calls if c["args"][3] == "success"]
    assert len(success_calls) == 1, f"expected 1 success log call, got {len(success_calls)}: {[c['args'] for c in calls]}"
    stage_name = success_calls[0]["args"][2]
    assert stage_name == "weekly:quality", (
        f"stage name must start with 'weekly:' to match dashboard filter "
        f"(pipeline_type LIKE 'weekly:%'), got '{stage_name}'"
    )


def test_weekly_quality_success_log_includes_usage_cost():
    """Regression: usage= kwarg must be passed so pipeline_logs.cost_usd populates."""
    calls = _run_weekly_quality_with_mocks()
    success_calls = [c for c in calls if c["args"][3] == "success"]
    assert len(success_calls) == 1
    usage = success_calls[0]["kwargs"].get("usage")
    assert usage is not None, "usage= kwarg missing — pipeline_logs.cost_usd will be NULL"
    assert usage.get("cost_usd") is not None and usage["cost_usd"] > 0, (
        f"cost_usd must be populated and positive, got: {usage}"
    )
    # Two calls (expert + learner) × 10k prompt + 2k completion = 24k total
    assert usage.get("tokens_used", 0) == 24000, f"expected 24000 tokens, got {usage.get('tokens_used')}"
    assert usage.get("model_used") is not None, "model_used must be set"


def test_weekly_quality_skipped_log_uses_weekly_prefix():
    """Empty content path also uses weekly: prefix for dashboard consistency."""
    import services.pipeline  # noqa: F401 — resolve circular import before touching pipeline_quality
    from services.pipeline_quality import _check_weekly_quality

    log_stage_calls: list[dict] = []

    async def fake_log_stage(*args, **kwargs):
        log_stage_calls.append({"args": args, "kwargs": kwargs})

    supabase = MagicMock()
    with patch("services.pipeline_quality._log_stage", side_effect=fake_log_stage):
        result = asyncio.run(_check_weekly_quality(
            content_expert_en="",  # triggers skip path
            content_learner_en="",
            content_expert_ko="",
            content_learner_ko="",
            source_urls=[],
            supabase=supabase,
            run_id="test-run-2",
            cumulative_usage={},
        ))

    assert result == {"quality_score": 0, "quality_flags": ["no_expert_content"]}
    assert len(log_stage_calls) == 1
    stage_name = log_stage_calls[0]["args"][2]
    status = log_stage_calls[0]["args"][3]
    assert stage_name == "weekly:quality"
    assert status == "skipped"


def test_weekly_quality_log_resilient_when_one_try_fails():
    """If learner call fails, expert_usage still drives the merged cost log."""
    import services.pipeline  # noqa: F401 — resolve circular import before touching pipeline_quality
    from services.pipeline_quality import _check_weekly_quality

    mock_client = MagicMock()
    # First call (expert) succeeds; second call (learner) raises
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[_mock_qc_response(), Exception("learner boom")],
    )
    log_stage_calls: list[dict] = []

    async def fake_log_stage(*args, **kwargs):
        log_stage_calls.append({"args": args, "kwargs": kwargs})

    supabase = MagicMock()
    with patch("services.pipeline_quality.get_openai_client", return_value=mock_client), \
         patch("services.pipeline_quality._log_stage", side_effect=fake_log_stage):
        asyncio.run(_check_weekly_quality(
            content_expert_en="English expert content. " * 500,
            content_learner_en="English learner content. " * 500,
            content_expert_ko="한국어 전문가 콘텐츠. " * 500,
            content_learner_ko="한국어 입문자 콘텐츠. " * 500,
            source_urls=[],
            supabase=supabase,
            run_id="test-run-3",
            cumulative_usage={},
        ))

    success_calls = [c for c in log_stage_calls if c["args"][3] == "success"]
    assert len(success_calls) == 1
    usage = success_calls[0]["kwargs"].get("usage")
    assert usage is not None and usage.get("cost_usd", 0) > 0, (
        f"expert cost alone must still be captured when learner fails, got: {usage}"
    )
    # Only expert succeeded: 10k + 2k = 12k tokens
    assert usage.get("tokens_used") == 12000

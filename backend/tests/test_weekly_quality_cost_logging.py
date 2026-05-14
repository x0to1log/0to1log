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


def _mock_perfect_qc_response(prompt_tokens: int = 10000, completion_tokens: int = 2000):
    """Build a mocked v2 weekly quality response with all sub-scores at 10."""
    rubric = {
        "structural_completeness": {
            "sections_present": {"evidence": "all sections", "score": 10},
            "section_depth": {"evidence": "deep", "score": 10},
        },
        "source_quality": {
            "citation_coverage": {"evidence": "all cited", "score": 10},
            "primary_source_priority": {"evidence": "official first", "score": 10},
            "source_utilization": {"evidence": "distributed", "score": 10},
        },
        "strategic_synthesis": {
            "trend_connection": {"evidence": "connected", "score": 10},
            "impact_framing": {"evidence": "decision-grade", "score": 10},
            "decision_relevance": {"evidence": "concrete", "score": 10},
        },
        "language_quality": {
            "fluency": {"evidence": "fluent", "score": 10},
            "locale_integrity": {"evidence": "clean", "score": 10},
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


def _weekly_body_with_missing_action_citation() -> str:
    top_stories = "\n\n".join(
        f"### Story {i}\n\nOpenAI and Amazon announced a capacity update. [1](https://openai.com/index/amazon-partnership/)"
        for i in range(1, 6)
    )
    return (
        "## This Week in One Line\n"
        "OpenAI and Amazon aligned capacity for agent workflows.\n\n"
        "## Week in Numbers\n"
        "- **2 GW** — OpenAI's Trainium capacity commitment. [1](https://openai.com/index/amazon-partnership/)\n\n"
        "## Top Stories\n\n"
        f"{top_stories}\n\n"
        "## Trend Analysis\n"
        "Capacity commitments became part of the product story. [1](https://openai.com/index/amazon-partnership/)\n\n"
        "## Watch Points\n"
        "- Capacity ramp timing. [1](https://openai.com/index/amazon-partnership/)\n\n"
        "## Open Source Spotlight\n"
        "- **Agent Governance Toolkit** — Guardrails for agents. [microsoft/agent-governance-toolkit](https://github.com/microsoft/agent-governance-toolkit)\n\n"
        "## So What Do I Do?\n"
        "- **If you rely on frontier APIs**: reserve capacity now — because access is becoming a procurement issue.\n"
    )


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


def test_weekly_quality_applies_guardrail_cap_for_missing_action_citation():
    """Sparse weekly citation misses should cap the final score even with perfect LLM QC."""
    import services.pipeline  # noqa: F401 — resolve circular import before touching pipeline_quality
    from services.pipeline_quality import _check_weekly_quality

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_perfect_qc_response(),
    )

    async def fake_log_stage(*args, **kwargs):
        return None

    body = _weekly_body_with_missing_action_citation()
    supabase = MagicMock()
    with patch("services.pipeline_quality.get_openai_client", return_value=mock_client), \
         patch("services.pipeline_quality._log_stage", side_effect=fake_log_stage):
        result = asyncio.run(_check_weekly_quality(
            content_expert_en=body,
            content_learner_en=body.replace("## So What Do I Do?", "## What Can I Try?"),
            content_expert_ko=body.replace("## So What Do I Do?", "## 그래서 나는?"),
            content_learner_ko=body.replace("## So What Do I Do?", "## 이번 주 해볼 것"),
            source_urls=["https://openai.com/index/amazon-partnership/"],
            supabase=supabase,
            run_id="test-run-guardrail",
            cumulative_usage={},
        ))

    assert result["quality_score"] <= 90
    assert "weekly_citation_contract_cap_90" in result["quality_caps_applied"]

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import openai
import pytest

from models.news_pipeline import PersonaOutput
from services.pipeline import _check_digest_quality


def response(payload, tier="default"):
    result = MagicMock()
    result.choices[0].message.content = json.dumps(payload) if payload else ""
    result.service_tier = tier
    result.usage.prompt_tokens = 100
    result.usage.completion_tokens = 50
    result.usage.total_tokens = 150
    result.usage.prompt_tokens_details = None
    result.usage.completion_tokens_details = None
    return result


def capacity_error(code="flex_unavailable"):
    return openai.RateLimitError(
        "capacity unavailable",
        response=httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com")),
        body={"code": code, "type": "resource_unavailable"},
    )


async def check(create):
    client = MagicMock()
    client.chat.completions.create = create
    with patch("services.pipeline_quality.get_openai_client", return_value=client), \
         patch("services.pipeline_quality._log_stage", new_callable=AsyncMock) as log:
        try:
            result = await _check_digest_quality(
                personas={"expert": PersonaOutput(en="English body", ko="Korean body")},
                digest_type="research", classified=[], community_summary_map={},
                supabase=MagicMock(), run_id="test-run", cumulative_usage={},
            )
        except RuntimeError as error:
            return error, log
    return result, log


@pytest.mark.asyncio
async def test_capacity_failure_retries_only_quality_with_default_tier():
    async def create(**kwargs):
        if kwargs["service_tier"] == "flex":
            raise capacity_error()
        return response({"score": 90, "issues": []})

    create_mock = AsyncMock(side_effect=create)
    result, log = await check(create_mock)
    assert isinstance(result, dict)
    assert result["quality_breakdown"]["raw_llm"]["expert_body"] == 90
    assert [c.kwargs["service_tier"] for c in create_mock.call_args_list] == [
        "flex", "default", "flex", "default",
    ]
    assert log.call_args.kwargs["usage"]["tokens_used"] == 300
    assert log.call_args.kwargs["usage"]["service_tier"] == "default"


@pytest.mark.asyncio
async def test_exhausted_quality_is_failure_not_a_deterministic_only_score():
    result, log = await check(AsyncMock(side_effect=capacity_error()))
    assert isinstance(result, RuntimeError)
    assert "Quality evaluation unavailable" in str(result)
    assert log.call_args.args[3] == "failed"
    assert log.call_args.kwargs["debug_meta"]["evaluation_failed"] is True
    assert len(log.call_args.kwargs["debug_meta"]["failed_evaluations"]) == 2


@pytest.mark.asyncio
async def test_quota_failure_does_not_switch_to_a_more_expensive_tier():
    create = AsyncMock(side_effect=capacity_error("insufficient_quota"))
    result, _ = await check(create)
    assert isinstance(result, RuntimeError)
    assert all(c.kwargs["service_tier"] == "flex" for c in create.call_args_list)


@pytest.mark.asyncio
async def test_empty_paid_responses_are_included_in_failed_stage_usage():
    result, log = await check(AsyncMock(return_value=response(None, "flex")))
    assert isinstance(result, RuntimeError)
    assert log.call_args.kwargs["usage"]["tokens_used"] == 600


@pytest.mark.asyncio
async def test_valid_zero_score_is_not_an_evaluation_failure():
    result, log = await check(AsyncMock(return_value=response({"score": 0, "issues": []})))
    assert isinstance(result, dict)
    assert result["quality_breakdown"]["raw_llm"]["expert_body"] == 0
    assert log.call_args.args[3] == "success"

"""Tests for _translate_focus_items_ko — the fallback helper that patches
missing focus_items_ko from the daily writer."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_openai_response(payload: dict):
    response = MagicMock()
    response.choices[0].message.content = json.dumps(payload, ensure_ascii=False)
    response.usage = MagicMock()
    response.usage.prompt_tokens = 200
    response.usage.completion_tokens = 80
    response.usage.total_tokens = 280
    return response


@pytest.mark.asyncio
async def test_translate_focus_items_ko_happy_path_returns_three_korean_items():
    """When the mini model returns 3 valid KO bullets, helper yields them."""
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response({
            "focus_items_ko": [
                "OpenAI가 GPT-5.4 출시",
                "컴퓨터 사용 에이전트 벤치마크 개선",
                "툴 지연 비용을 주시",
            ]
        })
    )

    from services.pipeline import _translate_focus_items_ko

    with patch("services.pipeline_digest.get_openai_client", return_value=fake_client):
        items, usage = await _translate_focus_items_ko(
            [
                "OpenAI releases GPT-5.4 with native computer use",
                "Benchmarks show large gains on agent tasks",
                "Watch tool yield latency and long-context costs",
            ],
            digest_type="research",
        )

    assert len(items) == 3
    assert all(isinstance(x, str) and x.strip() for x in items)
    assert items[0] == "OpenAI가 GPT-5.4 출시"
    assert usage.get("input_tokens") == 200
    assert usage.get("output_tokens") == 80


@pytest.mark.asyncio
async def test_translate_focus_items_ko_invalid_count_returns_empty():
    """If the mini model returns wrong count (e.g. 2 items instead of 3),
    helper returns empty so the caller doesn't ship a partial list."""
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response({
            "focus_items_ko": ["하나만", "둘"],  # only 2, not 3
        })
    )

    from services.pipeline import _translate_focus_items_ko

    with patch("services.pipeline_digest.get_openai_client", return_value=fake_client):
        items, usage = await _translate_focus_items_ko(
            ["A", "B", "C"], digest_type="business",
        )

    assert items == []
    assert usage == {}


@pytest.mark.asyncio
async def test_translate_focus_items_ko_llm_exception_is_swallowed():
    """LLM/network errors must not crash the pipeline — return ([], {}).
    The QC will then still flag the missing KO frontload, which is the
    correct fallback behavior (degrade gracefully, surface the gap)."""
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("openai 500"))

    from services.pipeline import _translate_focus_items_ko

    with patch("services.pipeline_digest.get_openai_client", return_value=fake_client):
        items, usage = await _translate_focus_items_ko(
            ["A", "B", "C"], digest_type="research",
        )

    assert items == []
    assert usage == {}


@pytest.mark.asyncio
async def test_translate_focus_items_ko_noop_when_input_not_three():
    """Helper skips the LLM call entirely if input isn't exactly 3 items —
    translating partial lists would ship a broken frontload."""
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock()

    from services.pipeline import _translate_focus_items_ko

    with patch("services.pipeline_digest.get_openai_client", return_value=fake_client):
        items_empty, _ = await _translate_focus_items_ko([], digest_type="research")
        items_two, _ = await _translate_focus_items_ko(["A", "B"], digest_type="research")

    assert items_empty == []
    assert items_two == []
    # LLM must NOT have been called for either invalid input
    assert fake_client.chat.completions.create.await_count == 0

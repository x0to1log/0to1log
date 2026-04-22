"""Phase 1 of NQ-40: verify quotes_ko Hangul validation + retranslation
fallback in summarize_community prevents English from leaking into the
Korean Community Pulse section."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_openai_response(payload: dict):
    response = MagicMock()
    response.choices[0].message.content = json.dumps(payload, ensure_ascii=False)
    response.usage = MagicMock()
    response.usage.prompt_tokens = 200
    response.usage.completion_tokens = 100
    response.usage.total_tokens = 300
    return response


def test_has_hangul_detects_korean_content():
    from services.agents.ranking import _has_hangul

    assert _has_hangul("안녕하세요") is True
    assert _has_hangul("OpenAI가 GPT-5.4 출시") is True  # mixed ok
    assert _has_hangul("Hello world") is False
    assert _has_hangul("That paper focuses on breaking") is False
    assert _has_hangul("") is False
    assert _has_hangul(None) is False
    # Edge: Korean characters outside the Hangul syllable block shouldn't count
    assert _has_hangul("ㄱㄴㄷ") is False  # compatibility jamo, not full syllables


@pytest.mark.asyncio
async def test_retranslate_quotes_ko_happy_path_returns_korean():
    """Given 2 EN quotes, the mini model returns 2 Korean translations in order."""
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response({
            "quotes_ko": [
                "그 논문은 테스트 환경을 깨뜨리는 데 초점을 맞추고 있습니다.",
                "LLM은 실제로 수학을 계산하지 않습니다.",
            ],
        })
    )

    from services.agents.ranking import _retranslate_quotes_ko_async

    with patch("services.agents.ranking.get_openai_client", return_value=fake_client):
        translated, usage = await _retranslate_quotes_ko_async([
            "That paper focuses on breaking the test harness.",
            "LLMs do not actually compute math.",
        ])

    assert len(translated) == 2
    from services.agents.ranking import _has_hangul
    assert all(_has_hangul(t) for t in translated)
    # Usage metrics propagated from the mini call
    assert usage.get("input_tokens") == 200


@pytest.mark.asyncio
async def test_retranslate_quotes_ko_wrong_count_returns_empty():
    """If the mini model returns a different item count, caller drops the
    affected quotes rather than ship a misaligned translation."""
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response({"quotes_ko": ["하나만"]})  # expected 2
    )

    from services.agents.ranking import _retranslate_quotes_ko_async

    with patch("services.agents.ranking.get_openai_client", return_value=fake_client):
        translated, usage = await _retranslate_quotes_ko_async(["a", "b"])

    assert translated == []
    assert usage == {}


@pytest.mark.asyncio
async def test_retranslate_quotes_ko_llm_exception_returns_empty():
    """LLM/network errors must not crash the pipeline — caller drops."""
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("openai 500"))

    from services.agents.ranking import _retranslate_quotes_ko_async

    with patch("services.agents.ranking.get_openai_client", return_value=fake_client):
        translated, usage = await _retranslate_quotes_ko_async(["x"])

    assert translated == []
    assert usage == {}


@pytest.mark.asyncio
async def test_retranslate_empty_input_is_noop():
    """Empty input → no LLM call, empty return. Guard against wasted invocations."""
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock()

    from services.agents.ranking import _retranslate_quotes_ko_async

    with patch("services.agents.ranking.get_openai_client", return_value=fake_client):
        translated, usage = await _retranslate_quotes_ko_async([])

    assert translated == []
    assert usage == {}
    assert fake_client.chat.completions.create.await_count == 0

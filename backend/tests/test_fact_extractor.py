"""Tests for LLM fact extraction agent."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_openai_response(data: dict, tokens: int = 500):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = json.dumps(data)
    mock_resp.usage = MagicMock()
    mock_resp.usage.prompt_tokens = 2000
    mock_resp.usage.completion_tokens = tokens
    mock_resp.usage.total_tokens = 2000 + tokens
    return mock_resp


SAMPLE_FACT_PACK = {
    "headline": "OpenAI releases GPT-5 with 95% MMLU score",
    "key_facts": [
        {
            "id": "f1",
            "claim": "GPT-5 scores 95% on MMLU benchmark",
            "why_it_matters": "20% improvement over GPT-4",
            "source_ids": ["s1"],
            "confidence": "high",
        },
        {
            "id": "f2",
            "claim": "Available via API starting today",
            "why_it_matters": "Immediate developer access",
            "source_ids": ["s1"],
            "confidence": "high",
        },
    ],
    "numbers": [
        {"value": "95%", "context": "MMLU score", "source_id": "s1"},
        {"value": "20%", "context": "improvement over GPT-4", "source_id": "s1"},
    ],
    "entities": [
        {"name": "OpenAI", "role": "developer", "url": "https://openai.com"},
    ],
    "sources": [
        {
            "id": "s1",
            "title": "GPT-5 Announcement",
            "publisher": "openai.com",
            "url": "https://openai.com/blog/gpt-5",
            "published_at": "2026-03-15",
        },
    ],
    "community_summary": "Developers excited but waiting for independent benchmarks.",
}


@pytest.mark.asyncio
async def test_extract_facts_returns_valid_fact_pack():
    """Happy path: extract facts from news text."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(SAMPLE_FACT_PACK)

    with patch("services.agents.fact_extractor.get_openai_client", return_value=mock_client), \
         patch("services.agents.fact_extractor.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.fact_extractor import extract_facts
        fact_pack, usage = await extract_facts(
            news_text="OpenAI released GPT-5 today...",
            context_text="Additional Tavily context...",
            community_text="Reddit says it's great.",
        )

    assert fact_pack.headline == "OpenAI releases GPT-5 with 95% MMLU score"
    assert len(fact_pack.key_facts) == 2
    assert fact_pack.key_facts[0].id == "f1"
    assert len(fact_pack.sources) == 1
    assert usage["tokens_used"] > 0


@pytest.mark.asyncio
async def test_extract_facts_with_empty_community():
    """Community text can be empty."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(SAMPLE_FACT_PACK)

    with patch("services.agents.fact_extractor.get_openai_client", return_value=mock_client), \
         patch("services.agents.fact_extractor.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.fact_extractor import extract_facts
        fact_pack, usage = await extract_facts(
            news_text="Some news text",
            context_text="",
            community_text="",
        )

    assert fact_pack is not None
    # Verify prompt was built (community section should still be present but empty)
    call_args = mock_client.chat.completions.create.call_args
    user_msg = call_args[1]["messages"][1]["content"]
    assert "Community Reactions" in user_msg


@pytest.mark.asyncio
async def test_extract_facts_retries_on_json_error():
    """JSON parse failure triggers retry."""
    bad_resp = MagicMock()
    bad_resp.choices = [MagicMock()]
    bad_resp.choices[0].message.content = "invalid json..."
    bad_resp.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

    good_resp = _mock_openai_response(SAMPLE_FACT_PACK)

    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = [bad_resp, good_resp]

    with patch("services.agents.fact_extractor.get_openai_client", return_value=mock_client), \
         patch("services.agents.fact_extractor.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.fact_extractor import extract_facts
        fact_pack, usage = await extract_facts(
            news_text="News text",
            context_text="Context",
            community_text="Reactions",
        )

    assert fact_pack is not None
    assert mock_client.chat.completions.create.call_count == 2


@pytest.mark.asyncio
async def test_extract_facts_all_retries_fail_raises():
    """If all retries fail, raise the error."""
    bad_resp = MagicMock()
    bad_resp.choices = [MagicMock()]
    bad_resp.choices[0].message.content = "not json"
    bad_resp.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = bad_resp

    with patch("services.agents.fact_extractor.get_openai_client", return_value=mock_client), \
         patch("services.agents.fact_extractor.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.fact_extractor import extract_facts
        with pytest.raises(Exception):
            await extract_facts(
                news_text="News text",
                context_text="Context",
                community_text="Reactions",
            )

"""Tests for classification-stage ranking helpers."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.news_pipeline import NewsCandidate


def _mock_openai_response(data: dict, tokens: int = 300):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = json.dumps(data)
    mock_resp.usage = MagicMock()
    mock_resp.usage.prompt_tokens = 1000
    mock_resp.usage.completion_tokens = tokens
    mock_resp.usage.total_tokens = 1000 + tokens
    return mock_resp


SAMPLE_CANDIDATES = [
    NewsCandidate(title="GPT-5 Released", url="https://a.com/1", snippet="Major model release", source="tavily"),
    NewsCandidate(title="AI Startup raises $500M", url="https://b.com/2", snippet="Funding round", source="tavily"),
    NewsCandidate(title="New transformer paper", url="https://c.com/3", snippet="Architecture improvement", source="tavily"),
]


CLASSIFICATION_LLM_RESPONSE = {
    "research": [
        {"url": "https://c.com/3", "subcategory": "papers", "reason": "Novel architecture", "score": 0.92},
        {"url": "https://a.com/1", "subcategory": "llm_models", "reason": "Major release", "score": 0.88},
    ],
    "business": [
        {"url": "https://b.com/2", "subcategory": "industry", "reason": "Major funding", "score": 0.90},
        {"url": "https://a.com/1", "subcategory": "big_tech", "reason": "GPT-5 market impact", "score": 0.85},
    ],
}


def test_legacy_rank_candidates_api_removed():
    from services.agents import ranking

    assert not hasattr(ranking, "rank_candidates")


@pytest.mark.asyncio
async def test_classify_candidates_returns_multiple_picks_and_prompt():
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(CLASSIFICATION_LLM_RESPONSE)

    with patch("services.agents.ranking.get_openai_client", return_value=mock_client), \
         patch("services.agents.ranking.settings") as mock_settings:
        mock_settings.openai_model_light = "gpt-4o"

        from services.agents.ranking import classify_candidates
        result, usage, user_prompt = await classify_candidates(SAMPLE_CANDIDATES)

    assert len(result.research_picks) == 2
    assert len(result.business_picks) == 2
    assert result.research_picks[0].subcategory == "papers"
    assert result.business_picks[0].subcategory == "industry"
    assert any(c.url == "https://a.com/1" for c in result.research_picks)
    assert any(c.url == "https://a.com/1" for c in result.business_picks)
    assert "[1] GPT-5 Released" in user_prompt
    assert usage["tokens_used"] > 0


@pytest.mark.asyncio
async def test_classify_candidates_empty_list_returns_empty_result():
    from services.agents.ranking import classify_candidates

    result, usage, user_prompt = await classify_candidates([])

    assert result.research_picks == []
    assert result.business_picks == []
    assert usage == {}
    assert user_prompt == ""

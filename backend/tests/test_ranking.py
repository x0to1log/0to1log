"""Tests for LLM news ranking agent."""
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

RANKING_LLM_RESPONSE = {
    "research": {"url": "https://c.com/3", "reason": "Novel architecture", "score": 0.92},
    "business": {"url": "https://b.com/2", "reason": "Major funding", "score": 0.88},
}


@pytest.mark.asyncio
async def test_rank_candidates_selects_research_and_business():
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(RANKING_LLM_RESPONSE)

    with patch("services.agents.ranking.get_openai_client", return_value=mock_client), \
         patch("services.agents.ranking.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.ranking import rank_candidates
        result, usage = await rank_candidates(SAMPLE_CANDIDATES)

    assert result.research is not None
    assert result.research.url == "https://c.com/3"
    assert result.research.assigned_type == "research"
    assert result.business is not None
    assert result.business.url == "https://b.com/2"
    assert result.business.assigned_type == "business"
    assert usage["tokens_used"] > 0


@pytest.mark.asyncio
async def test_rank_candidates_no_research():
    response_data = {"research": None, "business": {"url": "https://b.com/2", "reason": "Important", "score": 0.85}}
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(response_data)

    with patch("services.agents.ranking.get_openai_client", return_value=mock_client), \
         patch("services.agents.ranking.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.ranking import rank_candidates
        result, usage = await rank_candidates(SAMPLE_CANDIDATES)

    assert result.research is None
    assert result.business is not None


@pytest.mark.asyncio
async def test_rank_candidates_empty_list():
    from services.agents.ranking import rank_candidates
    result, usage = await rank_candidates([])
    assert result.research is None
    assert result.business is None
    assert usage == {}


@pytest.mark.asyncio
async def test_rank_candidates_json_parse_error_retries():
    good_response = _mock_openai_response(RANKING_LLM_RESPONSE)
    bad_response = MagicMock()
    bad_response.choices = [MagicMock()]
    bad_response.choices[0].message.content = "not valid json{{"
    bad_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = [bad_response, good_response]

    with patch("services.agents.ranking.get_openai_client", return_value=mock_client), \
         patch("services.agents.ranking.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.ranking import rank_candidates
        result, usage = await rank_candidates(SAMPLE_CANDIDATES)

    assert result.research is not None
    assert mock_client.chat.completions.create.call_count == 2


@pytest.mark.asyncio
async def test_rank_candidates_all_retries_fail_returns_empty():
    bad_response = MagicMock()
    bad_response.choices = [MagicMock()]
    bad_response.choices[0].message.content = "not valid json{{"
    bad_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

    mock_client = AsyncMock()
    # 3 total attempts (MAX_RETRIES=2 means 0,1,2 → 3 calls)
    mock_client.chat.completions.create.side_effect = [bad_response, bad_response, bad_response]

    with patch("services.agents.ranking.get_openai_client", return_value=mock_client), \
         patch("services.agents.ranking.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.ranking import rank_candidates
        result, usage = await rank_candidates(SAMPLE_CANDIDATES)

    assert result.research is None
    assert result.business is None
    assert usage == {}
    assert mock_client.chat.completions.create.call_count == 3

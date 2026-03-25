"""Tests for multi-source news collection service."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


TAVILY_SEARCH_RESPONSE = {
    "results": [
        {
            "title": "GPT-5 Released by OpenAI",
            "url": "https://openai.com/blog/gpt-5",
            "content": "OpenAI has released GPT-5 with significant improvements.",
            "raw_content": "Full article text...",
        },
        {
            "title": "Google Gemini 2.0 Update",
            "url": "https://blog.google/gemini-2",
            "content": "Google announces Gemini 2.0 with new capabilities.",
            "raw_content": "Full article text about Gemini...",
        },
    ]
}


def _patch_new_collectors():
    """Patch HF, arXiv, GitHub collectors to return empty lists."""
    return (
        patch("services.news_collection._collect_hf_papers", new_callable=AsyncMock, return_value=[]),
        patch("services.news_collection._collect_arxiv", new_callable=AsyncMock, return_value=[]),
        patch("services.news_collection._collect_github_trending", new_callable=AsyncMock, return_value=[]),
    )


@pytest.mark.asyncio
async def test_collect_news_returns_candidates():
    mock_tavily = MagicMock()
    mock_tavily.search.return_value = TAVILY_SEARCH_RESPONSE

    p1, p2, p3 = _patch_new_collectors()
    with patch("services.news_collection.TavilyClient", return_value=mock_tavily), \
         patch("services.news_collection.settings") as mock_settings, \
         p1, p2, p3:
        mock_settings.tavily_api_key = "test-key"

        from services.news_collection import collect_news
        candidates, meta = await collect_news()

    assert len(candidates) == 2
    assert candidates[0].title == "GPT-5 Released by OpenAI"
    assert candidates[0].url == "https://openai.com/blog/gpt-5"
    assert meta["is_backfill"] is False
    assert meta["total_candidates"] == 2
    mock_tavily.search.assert_called()


@pytest.mark.asyncio
async def test_collect_news_deduplicates_urls():
    duped_response = {
        "results": [
            {"title": "Article A", "url": "https://example.com/same", "content": "A", "raw_content": ""},
            {"title": "Article B", "url": "https://example.com/same", "content": "B", "raw_content": ""},
            {"title": "Article C", "url": "https://example.com/other", "content": "C", "raw_content": ""},
        ]
    }
    mock_tavily = MagicMock()
    mock_tavily.search.return_value = duped_response

    p1, p2, p3 = _patch_new_collectors()
    with patch("services.news_collection.TavilyClient", return_value=mock_tavily), \
         patch("services.news_collection.settings") as mock_settings, \
         p1, p2, p3:
        mock_settings.tavily_api_key = "test-key"

        from services.news_collection import collect_news
        candidates, meta = await collect_news()

    assert len(candidates) == 2
    assert meta["total_candidates"] == 2


@pytest.mark.asyncio
async def test_collect_news_no_api_key_returns_empty():
    p1, p2, p3 = _patch_new_collectors()
    with patch("services.news_collection.settings") as mock_settings, \
         p1, p2, p3:
        mock_settings.tavily_api_key = ""

        from services.news_collection import collect_news
        candidates, meta = await collect_news()

    assert candidates == []
    assert meta["total_candidates"] == 0


@pytest.mark.asyncio
async def test_collect_news_api_error_returns_empty():
    mock_tavily = MagicMock()
    mock_tavily.search.side_effect = Exception("API rate limit")

    p1, p2, p3 = _patch_new_collectors()
    with patch("services.news_collection.TavilyClient", return_value=mock_tavily), \
         patch("services.news_collection.settings") as mock_settings, \
         p1, p2, p3:
        mock_settings.tavily_api_key = "test-key"

        from services.news_collection import collect_news
        candidates, meta = await collect_news()

    assert candidates == []
    assert meta["total_candidates"] == 0


TAVILY_REACTION_RESPONSE = {
    "results": [
        {
            "url": "https://reddit.com/r/MachineLearning/abc",
            "content": "This is a game changer. The benchmark improvements are real.",
        },
        {
            "url": "https://news.ycombinator.com/item?id=123",
            "content": "Skeptical about the claims. Need to see independent benchmarks.",
        },
    ]
}


@pytest.mark.asyncio
async def test_collect_community_reactions_returns_text():
    """Community reactions should return combined text."""
    mock_tavily = MagicMock()
    mock_tavily.search.return_value = TAVILY_REACTION_RESPONSE

    with patch("services.news_collection.TavilyClient", return_value=mock_tavily), \
         patch("services.news_collection.settings") as mock_settings:
        mock_settings.tavily_api_key = "test-key"

        from services.news_collection import collect_community_reactions
        text = await collect_community_reactions("GPT-5 Released", "https://openai.com/gpt5")

    assert "game changer" in text
    assert "reddit.com" in text


@pytest.mark.asyncio
async def test_collect_community_reactions_no_api_key():
    """Missing API key returns empty string."""
    with patch("services.news_collection.settings") as mock_settings:
        mock_settings.tavily_api_key = ""

        from services.news_collection import collect_community_reactions
        text = await collect_community_reactions("Title", "https://example.com")

    assert text == ""


@pytest.mark.asyncio
async def test_collect_community_reactions_api_error():
    """API error returns empty string, not crash."""
    mock_tavily = MagicMock()
    mock_tavily.search.side_effect = Exception("Timeout")

    with patch("services.news_collection.TavilyClient", return_value=mock_tavily), \
         patch("services.news_collection.settings") as mock_settings:
        mock_settings.tavily_api_key = "test-key"

        from services.news_collection import collect_community_reactions
        text = await collect_community_reactions("Title", "https://example.com")

    assert text == ""


@pytest.mark.asyncio
async def test_collect_community_reactions_client_construction_error():
    """TavilyClient construction failure returns empty string, not crash."""
    with patch("services.news_collection.TavilyClient", side_effect=Exception("bad key")), \
         patch("services.news_collection.settings") as mock_settings:
        mock_settings.tavily_api_key = "test-key"

        from services.news_collection import collect_community_reactions
        text = await collect_community_reactions("Title", "https://example.com")

    assert text == ""

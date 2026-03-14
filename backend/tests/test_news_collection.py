"""Tests for Tavily news collection service."""
from unittest.mock import MagicMock, patch

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


@pytest.mark.asyncio
async def test_collect_news_returns_candidates():
    mock_tavily = MagicMock()
    mock_tavily.search.return_value = TAVILY_SEARCH_RESPONSE

    with patch("services.news_collection.TavilyClient", return_value=mock_tavily), \
         patch("services.news_collection.settings") as mock_settings:
        mock_settings.tavily_api_key = "test-key"

        from services.news_collection import collect_news
        candidates = await collect_news()

    assert len(candidates) == 2
    assert candidates[0].title == "GPT-5 Released by OpenAI"
    assert candidates[0].url == "https://openai.com/blog/gpt-5"
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

    with patch("services.news_collection.TavilyClient", return_value=mock_tavily), \
         patch("services.news_collection.settings") as mock_settings:
        mock_settings.tavily_api_key = "test-key"

        from services.news_collection import collect_news
        candidates = await collect_news()

    assert len(candidates) == 2


@pytest.mark.asyncio
async def test_collect_news_no_api_key_returns_empty():
    with patch("services.news_collection.settings") as mock_settings:
        mock_settings.tavily_api_key = ""

        from services.news_collection import collect_news
        candidates = await collect_news()

    assert candidates == []


@pytest.mark.asyncio
async def test_collect_news_api_error_returns_empty():
    mock_tavily = MagicMock()
    mock_tavily.search.side_effect = Exception("API rate limit")

    with patch("services.news_collection.TavilyClient", return_value=mock_tavily), \
         patch("services.news_collection.settings") as mock_settings:
        mock_settings.tavily_api_key = "test-key"

        from services.news_collection import collect_news
        candidates = await collect_news()

    assert candidates == []

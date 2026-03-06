import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from models.ranking import NewsCandidate
from services.news_collection import (
    collect_from_tavily,
    collect_from_hackernews,
    collect_from_github_trending,
    collect_all_news,
    deduplicate_by_url,
    normalize_url,
)


# ============================================================
# URL normalization + deduplication
# ============================================================

def test_normalize_url_strips_fragment():
    assert normalize_url("https://example.com/page#section") == "https://example.com/page"


def test_normalize_url_strips_trailing_slash():
    assert normalize_url("https://example.com/page/") == "https://example.com/page"


def test_normalize_url_lowercases_host():
    assert normalize_url("https://EXAMPLE.COM/Page") == "https://example.com/Page"


def test_deduplicate_by_url_removes_duplicates():
    candidates = [
        NewsCandidate(title="A", url="https://example.com/a", snippet="s", source="tavily"),
        NewsCandidate(title="B", url="https://example.com/a/", snippet="s", source="hackernews"),
        NewsCandidate(title="C", url="https://other.com/b", snippet="s", source="github"),
    ]
    result = deduplicate_by_url(candidates)
    assert len(result) == 2
    assert result[0].title == "A"
    assert result[1].title == "C"


def test_deduplicate_empty_list():
    assert deduplicate_by_url([]) == []


# ============================================================
# Tavily collection (mocked)
# ============================================================

@pytest.mark.asyncio
async def test_tavily_collection():
    mock_tavily_results = {
        "results": [
            {"title": "AI News 1", "url": "https://ai.com/1", "content": "Some content about AI"},
            {"title": "AI News 2", "url": "https://ai.com/2", "content": "More AI content"},
            {"title": "AI News 3", "url": "https://ai.com/3", "content": "Even more"},
        ]
    }

    mock_client = MagicMock()
    mock_client.search.return_value = mock_tavily_results

    with patch("services.news_collection.settings") as mock_settings:
        mock_settings.tavily_api_key = "test-key"
        with patch("tavily.TavilyClient", return_value=mock_client):
            result = await collect_from_tavily("2026-03-06")

    assert len(result) == 12  # 4 queries × 3 results each
    assert all(c.source == "tavily" for c in result)
    assert result[0].title == "AI News 1"


@pytest.mark.asyncio
async def test_tavily_skips_when_no_api_key():
    with patch("services.news_collection.settings") as mock_settings:
        mock_settings.tavily_api_key = ""
        result = await collect_from_tavily("2026-03-06")
    assert result == []


# ============================================================
# Hacker News collection (mocked)
# ============================================================

@pytest.mark.asyncio
async def test_hackernews_collection():
    top_stories = [1, 2, 3, 4, 5]

    story_data = {
        1: {"type": "story", "title": "New GPT-5 Released", "url": "https://openai.com/gpt5"},
        2: {"type": "story", "title": "React 20 is out", "url": "https://react.dev/20"},
        3: {"type": "story", "title": "Anthropic raises $10B", "url": "https://anthropic.com/funding"},
        4: {"type": "story", "title": "LLM benchmark results", "url": "https://bench.ai/results"},
        5: {"type": "comment", "title": "Just a comment", "url": ""},
    }

    async def mock_get(url, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if "topstories" in url:
            resp.json.return_value = top_stories
        else:
            story_id = int(url.split("/")[-1].replace(".json", ""))
            resp.json.return_value = story_data.get(story_id, {})
        return resp

    with patch("services.news_collection.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await collect_from_hackernews()

    # Should filter: story 1 (GPT), 3 (Anthropic), 4 (LLM) match AI keywords
    # Story 2 (React) doesn't match, story 5 is a comment
    assert len(result) == 3
    assert all(c.source == "hackernews" for c in result)
    titles = [c.title for c in result]
    assert "New GPT-5 Released" in titles
    assert "React 20 is out" not in titles


# ============================================================
# GitHub Trending collection (mocked)
# ============================================================

@pytest.mark.asyncio
async def test_github_trending():
    github_response = {
        "items": [
            {"full_name": "org/ai-tool", "html_url": "https://github.com/org/ai-tool", "description": "An AI tool"},
            {"full_name": "org/llm-lib", "html_url": "https://github.com/org/llm-lib", "description": "LLM library"},
        ]
    }

    async def mock_get(url, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = github_response
        return resp

    with patch("services.news_collection.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await collect_from_github_trending()

    assert len(result) == 2
    assert all(c.source == "github" for c in result)
    assert result[0].title == "org/ai-tool"


# ============================================================
# collect_all_news integration (all sources mocked)
# ============================================================

@pytest.mark.asyncio
async def test_collect_all_news():
    tavily_candidates = [
        NewsCandidate(title="T1", url="https://a.com/1", snippet="s", source="tavily"),
    ]
    hn_candidates = [
        NewsCandidate(title="HN1", url="https://b.com/1", snippet="s", source="hackernews"),
        NewsCandidate(title="HN2", url="https://a.com/1", snippet="s", source="hackernews"),  # duplicate
    ]
    gh_candidates = [
        NewsCandidate(title="GH1", url="https://c.com/1", snippet="s", source="github"),
    ]

    with patch("services.news_collection.collect_from_tavily", return_value=tavily_candidates), \
         patch("services.news_collection.collect_from_hackernews", return_value=hn_candidates), \
         patch("services.news_collection.collect_from_github_trending", return_value=gh_candidates):
        result = await collect_all_news("2026-03-06")

    # 4 total, but a.com/1 is duplicated → 3 unique
    assert len(result) == 3


@pytest.mark.asyncio
async def test_collect_all_news_handles_source_failure():
    """One source fails, others still return results."""
    tavily_candidates = [
        NewsCandidate(title="T1", url="https://a.com/1", snippet="s", source="tavily"),
    ]

    with patch("services.news_collection.collect_from_tavily", return_value=tavily_candidates), \
         patch("services.news_collection.collect_from_hackernews", side_effect=Exception("HN down")), \
         patch("services.news_collection.collect_from_github_trending", return_value=[]):
        result = await collect_all_news("2026-03-06")

    assert len(result) == 1
    assert result[0].source == "tavily"

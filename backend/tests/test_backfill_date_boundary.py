"""Historical runs must not import evidence published after their target day."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.news_pipeline import NewsCandidate
from services import news_collection as collection


@pytest.fixture(autouse=True)
def isolated_clock_and_domains():
    with patch.object(collection, "today_kst", return_value="2026-09-07"), \
         patch.object(collection, "_load_domain_filters", return_value={
             name: frozenset() for name in ("block_non_en", "official_priority", "media_tier",
                                           "research_priority", "research_blocklist")
         }):
        yield


@pytest.mark.asyncio
async def test_release_selects_latest_eligible_history_not_latest_today():
    response = MagicMock(status_code=200)
    response.json.return_value = [
        {"tag_name": "1.17", "published_at": "2026-08-25T11:28:00Z"},
        {"tag_name": "1.16", "published_at": "2026-08-22T10:00:00Z"},
    ]
    client = SimpleNamespace(get=AsyncMock(return_value=response))
    result = await collection._fetch_latest_release(client, "langgenius/dify", datetime(2026, 8, 24))
    assert result["tag"] == "1.16"


@pytest.mark.asyncio
async def test_future_only_release_returns_none():
    response = MagicMock(status_code=200)
    response.json.return_value = [{"published_at": "2026-08-25T11:28:00Z"}]
    client = SimpleNamespace(get=AsyncMock(return_value=response))
    assert await collection._fetch_latest_release(client, "org/repo", datetime(2026, 8, 24)) is None


@pytest.mark.asyncio
async def test_tavily_retry_keeps_historical_end_date():
    client = MagicMock()
    client.search.side_effect = lambda **kw: {"results": []}
    with patch.object(collection, "TavilyClient", return_value=client), \
         patch.object(collection.settings, "tavily_api_key", "test"), \
         patch.object(collection, "_collect_fallback_news", AsyncMock(return_value=[])):
        _, meta = await collection._collect_tavily(10, "2026-08-24")
    assert meta["date_kwargs"] == {"start_date": "2026-08-23", "end_date": "2026-08-24"}
    assert all(call.kwargs.get("end_date") == "2026-08-24" for call in client.search.call_args_list)
    assert any(call.kwargs["start_date"] == "2026-08-19" for call in client.search.call_args_list)


@pytest.mark.asyncio
async def test_collection_drops_future_undated_and_updated_evidence():
    candidates = [
        NewsCandidate(title="AI release", url="https://openai.com/" + name,
                      snippet="AI model launch", published_at=date, raw_content=body)
        for name, date, body in [
            ("valid", "2026-08-24", "Original announcement"),
            ("future", "2026-08-25", "New announcement"),
            ("undated", "", "No evidence date"),
            ("updated", "2026-08-22", "Released 2026-08-25: new backend"),
        ]
    ]
    with patch.object(collection, "_collect_tavily", AsyncMock(return_value=(candidates, {}))), \
         patch.object(collection, "_collect_hf_papers", AsyncMock(return_value=[])), \
         patch.object(collection, "_collect_arxiv", AsyncMock(return_value=[])), \
         patch.object(collection, "_collect_github_trending", AsyncMock(return_value=[])), \
         patch.object(collection, "_collect_exa", AsyncMock(return_value=([], {}))):
        result, meta = await collection.collect_news(target_date="2026-08-24")
    assert [c.url for c in result] == ["https://openai.com/valid"]
    assert meta["historical_drop_counts"] == {"future": 2, "undated": 1}


@pytest.mark.asyncio
async def test_backfill_enrichment_uses_snapshot_without_live_lookup():
    group = SimpleNamespace(primary_url="https://openai.com/story", items=[
        SimpleNamespace(url="https://openai.com/story", title="AI launch")])
    with patch.object(collection, "_should_lookup_official_source", side_effect=AssertionError("live lookup")):
        result = await collection.enrich_sources([group], {group.primary_url: "Saved evidence"}, "2026-08-24")
    assert result[group.primary_url][0]["content"] == "Saved evidence"


@pytest.mark.asyncio
async def test_backfill_hf_does_not_fetch_mutable_paper_summary():
    with patch.object(collection.httpx, "AsyncClient") as client:
        assert await collection._collect_hf_papers("2026-08-24") == []
    client.assert_not_called()


@pytest.mark.asyncio
async def test_backfill_does_not_fetch_current_community_comments():
    with patch.object(collection.httpx, "AsyncClient") as client:
        assert await collection.collect_community_reactions("AI launch", "https://openai.com/story", "2026-08-24") == ""
    client.assert_not_called()


@pytest.mark.asyncio
async def test_arxiv_excludes_post_cutoff_revisions():
    response = MagicMock()
    response.text = '''<feed xmlns="http://www.w3.org/2005/Atom">
      <entry><id>http://arxiv.org/abs/2608.12345v2</id><title>Updated paper</title>
        <published>2026-08-24T10:00:00Z</published><updated>2026-08-26T10:00:00Z</updated></entry>
      <entry><id>http://arxiv.org/abs/2608.12346v1</id><title>Original paper</title>
        <published>2026-08-24T10:00:00Z</published><updated>2026-08-24T10:00:00Z</updated></entry>
    </feed>'''
    with patch.object(collection.httpx, "AsyncClient") as factory:
        factory.return_value.__aenter__.return_value.get = AsyncMock(return_value=response)
        results = await collection._collect_arxiv("2026-08-24")
    assert [item.url for item in results] == ["https://arxiv.org/abs/2608.12346v1"]
    assert results[0].published_at == "2026-08-24"


@pytest.mark.asyncio
async def test_historical_github_uses_only_dated_release_not_live_readme():
    response = MagicMock()
    response.json.return_value = {"items": [{"full_name": "org/repo", "html_url": "https://github.com/org/repo",
                                            "description": "LIVE DESCRIPTION", "stargazers_count": 9999}]}
    release = {"tag": "v1", "published_at": "2026-08-23", "body_excerpt": "Historical release",
               "prerelease": False, "html_url": "https://github.com/org/repo/releases/tag/v1"}
    with patch.object(collection.httpx, "AsyncClient") as factory, \
         patch.object(collection, "_fetch_latest_release", AsyncMock(return_value=release)), \
         patch.object(collection, "_fetch_readme_excerpt", AsyncMock()) as readme:
        factory.return_value.__aenter__.return_value.get = AsyncMock(return_value=response)
        result = await collection._collect_github_trending("2026-08-24")
    readme.assert_not_called()
    assert result[0].url == release["html_url"]
    assert result[0].published_at == "2026-08-23"
    assert "LIVE DESCRIPTION" not in result[0].raw_content
    assert "Historical release" in result[0].raw_content


@pytest.mark.parametrize("published,expected", [
    ("2026-08-17T23:59:00Z", True),
    ("2026-08-24T23:59:00Z", True),
    ("2026-08-16T23:59:00Z", False),
    ("2026-08-25T00:00:00Z", False),
])
@pytest.mark.asyncio
async def test_release_window_includes_only_target_day_and_previous_seven_days(published, expected):
    response = MagicMock(status_code=200)
    response.json.return_value = [{"published_at": published}]
    client = SimpleNamespace(get=AsyncMock(return_value=response))
    result = await collection._fetch_latest_release(client, "org/repo", datetime(2026, 8, 24))
    assert (result is not None) is expected


@pytest.mark.asyncio
async def test_backfill_fallback_does_not_query_unbounded_rss():
    with patch.object(collection.settings, "exa_api_key", ""), \
         patch.object(collection.httpx, "AsyncClient") as client:
        assert await collection._collect_fallback_news(["AI news"], {
            "start_date": "2026-08-19", "end_date": "2026-08-24",
        }) == []
    client.assert_not_called()


def test_unversioned_arxiv_rediscovery_is_not_historical_evidence():
    candidate = NewsCandidate(title="Paper", url="https://arxiv.org/abs/2608.21156",
                              published_at="2026-08-21", source="tavily")
    assert collection._historical_drop_reason(candidate, "2026-08-24") == "undated"

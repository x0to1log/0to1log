"""Tests for multi-source news collection service."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.config import settings


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


def test_classify_source_meta_marks_official_site_primary():
    from services.news_collection import _classify_source_meta

    meta = _classify_source_meta(
        url="https://openai.com/index/introducing-gpt-5-4/",
        source="tavily",
        title="Introducing GPT-5.4",
    )

    assert meta == {
        "source_kind": "official_site",
        "source_confidence": "high",
        "source_tier": "primary",
    }


def test_classify_source_meta_marks_hf_blog_as_official_platform_asset():
    from services.news_collection import _classify_source_meta

    meta = _classify_source_meta(
        url="https://huggingface.co/blog/Hcompany/holo3",
        source="tavily",
        title="Holo3",
    )

    assert meta["source_kind"] == "official_platform_asset"
    assert meta["source_confidence"] == "medium"
    assert meta["source_tier"] == "primary"


def test_classify_source_meta_marks_nvidia_developer_blog_as_official_site():
    from services.news_collection import _classify_source_meta

    meta = _classify_source_meta(
        url="https://developer.nvidia.com/blog/introducing-nemotron-3-super-an-open-hybrid-mamba-transformer-moe-for-agentic-reasoning",
        source="tavily",
        title="Introducing Nemotron 3 Super",
    )

    assert meta == {
        "source_kind": "official_site",
        "source_confidence": "high",
        "source_tier": "primary",
    }


def test_classify_source_meta_marks_microsoft_research_blog_as_official_site():
    from services.news_collection import _classify_source_meta

    meta = _classify_source_meta(
        url="https://www.microsoft.com/en-us/research/blog/fara-7b-an-efficient-agentic-model-for-computer-use/",
        source="tavily",
        title="Fara-7B: An Efficient Agentic Model for Computer Use",
    )

    assert meta == {
        "source_kind": "official_site",
        "source_confidence": "high",
        "source_tier": "primary",
    }


def test_classify_source_meta_marks_media_as_secondary():
    from services.news_collection import _classify_source_meta

    meta = _classify_source_meta(
        url="https://venturebeat.com/ai/story",
        source="tavily",
        title="VentureBeat coverage",
    )

    assert meta["source_kind"] == "media"
    assert meta["source_tier"] == "secondary"


def _patch_new_collectors():
    """Patch HF, arXiv, GitHub collectors to return empty lists."""
    return (
        patch("services.news_collection._collect_hf_papers", new_callable=AsyncMock, return_value=[]),
        patch("services.news_collection._collect_arxiv", new_callable=AsyncMock, return_value=[]),
        patch("services.news_collection._collect_github_trending", new_callable=AsyncMock, return_value=[]),
    )


def _patch_other_collectors():
    """Patch optional secondary collectors to keep collection tests deterministic."""
    # Brave news collection removed 2026-04-16; Brave web search still used by
    # collect_community_reactions() but that is a separate code path.
    return (
        patch(
            "services.news_collection._collect_exa",
            new_callable=AsyncMock,
            return_value=([], {"query_counts": {}, "errors": [], "business_total": 0, "total": 0}),
        ),
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
async def test_collect_news_attaches_source_metadata():
    mock_tavily = MagicMock()
    mock_tavily.search.return_value = TAVILY_SEARCH_RESPONSE

    p1, p2, p3 = _patch_new_collectors()
    (p4,) = _patch_other_collectors()
    with patch("services.news_collection.TavilyClient", return_value=mock_tavily), \
         patch("services.news_collection.settings") as mock_settings, \
         p1, p2, p3, p4:
        mock_settings.tavily_api_key = "test-key"

        from services.news_collection import collect_news
        candidates, _meta = await collect_news()

    assert candidates[0].source_kind == "official_site"
    assert candidates[0].source_confidence == "high"
    assert candidates[0].source_tier == "primary"


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
async def test_collect_exa_uses_daily_date_window_and_drops_stale_primary_result():
    from services.news_collection import _collect_exa

    mock_exa = MagicMock()
    mock_exa.search_and_contents.side_effect = [
        SimpleNamespace(
            results=[
                SimpleNamespace(
                    url="https://blogs.nvidia.com/blog/nemotron-3-super-agentic-ai/",
                    title="Nemotron 3 Super Advances Agentic AI",
                    text="NVIDIA announced Nemotron 3 Super.",
                    published_date="2026-03-11T00:00:00Z",
                ),
                SimpleNamespace(
                    url="https://openai.com/index/fresh-ai-launch/",
                    title="Fresh AI Launch",
                    text="OpenAI announced a fresh AI launch.",
                    published_date="2026-05-14T09:00:00Z",
                ),
            ]
        ),
        *[SimpleNamespace(results=[]) for _ in range(6)],
    ]

    with patch("services.news_collection.settings") as mock_settings, \
         patch.dict("sys.modules", {"exa_py": SimpleNamespace(Exa=lambda api_key: mock_exa)}):
        mock_settings.exa_api_key = "test-key"
        candidates, meta = await _collect_exa("2026-05-14")

    first_kwargs = mock_exa.search_and_contents.call_args_list[0].kwargs
    assert first_kwargs["start_published_date"] == "2026-05-12"
    assert first_kwargs["end_published_date"] == "2026-05-15"
    assert [candidate.url for candidate in candidates] == ["https://openai.com/index/fresh-ai-launch/"]
    assert candidates[0].published_at == "2026-05-14"
    assert meta["total"] == 1
    assert meta["query_counts"]["AI startup funding acquisition partnership"] == 1


@pytest.mark.asyncio
async def test_collect_exa_fallback_runs_when_business_queries_return_zero():
    from services.news_collection import _collect_exa

    empty = SimpleNamespace(results=[])
    fallback_result = SimpleNamespace(
        results=[
            SimpleNamespace(
                url="https://www.cnbc.com/2026/05/22/openai-business.html",
                title="OpenAI expands enterprise AI business",
                text="CNBC reported on May 22, 2026 that OpenAI expanded enterprise AI sales.",
                published_date="2026-05-22T00:00:00Z",
            )
        ]
    )
    mock_exa = MagicMock()
    mock_exa.search_and_contents.side_effect = [
        *[empty for _ in range(7)],
        fallback_result,
        *[empty for _ in range(4)],
    ]

    with patch("services.news_collection.settings") as mock_settings, \
         patch.dict("sys.modules", {"exa_py": SimpleNamespace(Exa=lambda api_key: mock_exa)}):
        mock_settings.exa_api_key = "test-key"
        candidates, meta = await _collect_exa("2026-05-23")

    assert [candidate.url for candidate in candidates] == ["https://www.cnbc.com/2026/05/22/openai-business.html"]
    assert meta["fallback_used"] is True
    assert meta["business_total"] == 1
    fallback_kwargs = mock_exa.search_and_contents.call_args_list[7].kwargs
    assert fallback_kwargs["start_published_date"] == "2026-05-19"
    assert fallback_kwargs["end_published_date"] == "2026-05-24"
    assert "category" not in fallback_kwargs


@pytest.mark.asyncio
async def test_collect_exa_fallback_skips_when_normal_business_results_exist():
    from services.news_collection import _collect_exa

    first_result = SimpleNamespace(
        results=[
            SimpleNamespace(
                url="https://blog.google/innovation-and-ai/business-update/",
                title="Google announces AI business update",
                text="Google announced a fresh AI business update.",
                published_date="2026-05-22T00:00:00Z",
            )
        ]
    )
    mock_exa = MagicMock()
    mock_exa.search_and_contents.side_effect = [
        first_result,
        *[SimpleNamespace(results=[]) for _ in range(6)],
    ]

    with patch("services.news_collection.settings") as mock_settings, \
         patch.dict("sys.modules", {"exa_py": SimpleNamespace(Exa=lambda api_key: mock_exa)}):
        mock_settings.exa_api_key = "test-key"
        candidates, meta = await _collect_exa("2026-05-23")

    assert len(candidates) == 1
    assert meta["fallback_used"] is False
    assert meta["business_total"] == 1
    assert mock_exa.search_and_contents.call_count == 7


@pytest.mark.asyncio
async def test_collect_news_records_business_candidate_health_and_exa_counts():
    from models.news_pipeline import NewsCandidate
    from services.news_collection import collect_news

    tavily_candidates = [
        NewsCandidate(
            title="OpenAI launches enterprise AI tool",
            url="https://www.cnbc.com/2026/05/22/openai-enterprise-ai.html",
            snippet="OpenAI launched a new enterprise AI tool on May 22, 2026.",
            source="tavily",
        )
    ]
    exa_meta = {
        "total": 0,
        "business_total": 0,
        "query_counts": {"AI startup funding acquisition partnership": 0},
        "errors": ["AI chip hardware Nvidia AMD Intel: timeout"],
        "fallback_used": True,
    }

    with patch("services.news_collection._collect_tavily", new=AsyncMock(return_value=(
            tavily_candidates,
            {
                "source": "tavily",
                "queries": ["big tech AI announcement OpenAI Google Microsoft Meta"],
                "query_counts": {"big tech AI announcement OpenAI Google Microsoft Meta": 1},
                "total_results": 1,
                "candidates": 1,
            },
         ))), \
         patch("services.news_collection._collect_hf_papers", new=AsyncMock(return_value=[])), \
         patch("services.news_collection._collect_arxiv", new=AsyncMock(return_value=[])), \
         patch("services.news_collection._collect_github_trending", new=AsyncMock(return_value=[])), \
         patch("services.news_collection._collect_exa", new=AsyncMock(return_value=([], exa_meta))):
        candidates, meta = await collect_news(target_date="2026-05-23")

    assert len(candidates) == 1
    health = meta["business_candidate_health"]
    assert health["business_like_count"] == 1
    assert health["trusted_business_like_count"] == 1
    assert health["exa_total"] == 0
    assert health["exa_business_total"] == 0
    assert health["exa_query_counts"] == exa_meta["query_counts"]
    assert health["exa_errors"] == exa_meta["errors"]
    assert health["tavily_query_counts"] == {"big tech AI announcement OpenAI Google Microsoft Meta": 1}


@pytest.mark.asyncio
async def test_collect_news_drops_stale_candidate_from_url_date():
    from models.news_pipeline import NewsCandidate
    from services.news_collection import collect_news

    stale = NewsCandidate(
        title="Canva launches its own design model",
        url="https://techcrunch.com/2025/10/30/canva-launches-ai-design-model/",
        snippet="Canva launches its own design model.",
        source="tavily",
    )
    fresh = NewsCandidate(
        title="OpenAI launches enterprise AI tool",
        url="https://www.cnbc.com/2026/05/22/openai-enterprise-ai.html",
        snippet="OpenAI launched a new enterprise AI tool.",
        source="tavily",
    )

    with patch("services.news_collection._collect_tavily", new=AsyncMock(return_value=([stale, fresh], {"query_counts": {}}))), \
         patch("services.news_collection._collect_hf_papers", new=AsyncMock(return_value=[])), \
         patch("services.news_collection._collect_arxiv", new=AsyncMock(return_value=[])), \
         patch("services.news_collection._collect_github_trending", new=AsyncMock(return_value=[])), \
         patch("services.news_collection._collect_exa", new=AsyncMock(return_value=([], {"query_counts": {}, "errors": [], "business_total": 0, "total": 0}))):
        candidates, meta = await collect_news(target_date="2026-05-23")

    assert [candidate.url for candidate in candidates] == [fresh.url]
    assert meta["stale_drop_counts"]["stale_url_date"] == 1


@pytest.mark.asyncio
async def test_collect_news_keeps_fresh_candidate_from_text_date_and_unknown_date():
    from models.news_pipeline import NewsCandidate
    from services.news_collection import collect_news

    fresh_text = NewsCandidate(
        title="OpenAI expands enterprise AI business",
        url="https://example.com/openai-enterprise-ai",
        snippet="CNBC reported on May 22, 2026 that OpenAI expanded enterprise AI sales.",
        source="tavily",
    )
    unknown = NewsCandidate(
        title="Anthropic updates its enterprise AI roadmap",
        url="https://example.com/anthropic-enterprise-ai",
        snippet="Anthropic described its enterprise AI roadmap.",
        source="tavily",
    )

    with patch("services.news_collection._collect_tavily", new=AsyncMock(return_value=([fresh_text, unknown], {"query_counts": {}}))), \
         patch("services.news_collection._collect_hf_papers", new=AsyncMock(return_value=[])), \
         patch("services.news_collection._collect_arxiv", new=AsyncMock(return_value=[])), \
         patch("services.news_collection._collect_github_trending", new=AsyncMock(return_value=[])), \
         patch("services.news_collection._collect_exa", new=AsyncMock(return_value=([], {"query_counts": {}, "errors": [], "business_total": 0, "total": 0}))):
        candidates, meta = await collect_news(target_date="2026-05-23")

    assert {candidate.url for candidate in candidates} == {fresh_text.url, unknown.url}
    assert meta["stale_drop_counts"]["stale_text_date"] == 0


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
    fallback_patch = patch("services.news_collection._collect_fallback_news", new_callable=AsyncMock, return_value=[])
    with patch("services.news_collection.TavilyClient", return_value=mock_tavily), \
         patch("services.news_collection.settings") as mock_settings, \
         p1, p2, p3, fallback_patch:
        mock_settings.tavily_api_key = "test-key"

        from services.news_collection import collect_news
        candidates, meta = await collect_news()

    assert candidates == []
    assert meta["total_candidates"] == 0


@pytest.mark.asyncio
async def test_enrich_sources_preserves_source_metadata():
    from models.news_pipeline import ClassifiedGroup, GroupedItem
    from services.news_collection import enrich_sources

    groups = [
        ClassifiedGroup(
            group_title="Official launch",
            items=[GroupedItem(url="https://openai.com/index/launch", title="Launch post")],
            category="business",
            subcategory="big_tech",
        )
    ]
    raw_content_map = {"https://openai.com/index/launch": "Launch content"}

    with patch("services.news_collection.settings") as mock_settings:
        mock_settings.exa_api_key = ""
        enriched = await enrich_sources(groups, raw_content_map)

    first = enriched["https://openai.com/index/launch"][0]
    assert first["source_kind"] == "official_site"
    assert first["source_confidence"] == "high"
    assert first["source_tier"] == "primary"


@pytest.mark.asyncio
async def test_enrich_sources_adds_official_source_for_secondary_lead_group():
    from models.news_pipeline import ClassifiedGroup, GroupedItem
    from services.news_collection import enrich_sources

    group = ClassifiedGroup(
        group_title="OpenAI Confirms Security Incident—Mac Users Must Update All Apps Now",
        items=[
            GroupedItem(
                url="https://www.forbes.com/sites/daveywinder/2026/04/12/openai-confirms-security-incident-mac-users-must-update-all-apps-now/",
                title="OpenAI Confirms Security Incident—Mac Users Must Update All Apps Now",
            )
        ],
        category="business",
        subcategory="big_tech",
        reason="[LEAD] Most important business story",
    )
    raw_content_map = {group.primary_url: "Forbes coverage"}

    mock_exa = MagicMock()
    mock_exa.search_and_contents.return_value = SimpleNamespace(
        results=[
            SimpleNamespace(
                url="https://openai.com/index/axios-developer-tool-compromise/",
                title="Our response to the Axios developer tool compromise",
                text="Official OpenAI response",
            )
        ]
    )
    mock_exa.find_similar_and_contents.return_value = SimpleNamespace(
        results=[
            SimpleNamespace(
                url="https://www.magzter.com/stories/technology/PC-WORLD/OPENAI-CONFIRMS-SECURITY-INCIDENT-MAC-USERS-MUST-UPDATE-APP-NOW",
                title="OpenAI Confirms Security Incident",
                text="Secondary coverage",
            )
        ]
    )

    with patch("services.news_collection.settings") as mock_settings, \
         patch.dict("sys.modules", {"exa_py": SimpleNamespace(Exa=lambda api_key: mock_exa)}):
        mock_settings.exa_api_key = "test-key"
        enriched = await enrich_sources([group], raw_content_map, target_date="2026-04-13")

    sources = enriched[group.primary_url]
    assert any(source["url"] == "https://openai.com/index/axios-developer-tool-compromise/" for source in sources)
    official = next(source for source in sources if source["url"] == "https://openai.com/index/axios-developer-tool-compromise/")
    assert official["source_tier"] == "primary"
    assert sources[1]["url"] == "https://openai.com/index/axios-developer-tool-compromise/"


@pytest.mark.asyncio
async def test_enrich_sources_checks_official_source_for_multi_source_secondary_lead_group():
    from models.news_pipeline import ClassifiedGroup, GroupedItem
    from services.news_collection import enrich_sources

    group = ClassifiedGroup(
        group_title="OpenAI launches Daybreak to automate software vulnerability defense",
        items=[
            GroupedItem(
                url="https://www.theverge.com/ai-artificial-intelligence/928342/openai-daybreak-security-ai",
                title="OpenAI just released its answer to Claude Mythos",
            ),
            GroupedItem(
                url="https://gizmodo.com/daybreak-openais-answer-to-anthropics-project-glasswing-has-arrived-2000757349",
                title="Daybreak: OpenAI's answer to Anthropic's Project Glasswing has arrived",
            ),
        ],
        category="business",
        subcategory="big_tech",
        reason="[LEAD] Most important business story",
    )
    raw_content_map = {
        group.items[0].url: "The Verge coverage",
        group.items[1].url: "Gizmodo coverage",
    }

    mock_exa = MagicMock()
    mock_exa.search_and_contents.return_value = SimpleNamespace(
        results=[
            SimpleNamespace(
                url="https://openai.com/daybreak/",
                title="Daybreak",
                text="Official OpenAI Daybreak page",
            )
        ]
    )
    mock_exa.find_similar_and_contents.return_value = SimpleNamespace(results=[])

    with patch("services.news_collection.settings") as mock_settings, \
         patch.dict("sys.modules", {"exa_py": SimpleNamespace(Exa=lambda api_key: mock_exa)}):
        mock_settings.exa_api_key = "test-key"
        enriched = await enrich_sources([group], raw_content_map, target_date="2026-05-13")

    sources = enriched[group.primary_url]
    assert [source["url"] for source in sources[:2]] == [group.items[0].url, group.items[1].url]
    official = next(source for source in sources if source["url"] == "https://openai.com/daybreak/")
    assert official["source_kind"] == "official_site"
    assert official["source_tier"] == "primary"
    mock_exa.find_similar_and_contents.assert_not_called()


@pytest.mark.asyncio
async def test_official_lookup_retries_without_date_filter_when_dated_search_misses_static_page():
    from models.news_pipeline import ClassifiedGroup, GroupedItem
    from services.news_collection import enrich_sources

    group = ClassifiedGroup(
        group_title="OpenAI launches Daybreak to automate software vulnerability defense",
        items=[
            GroupedItem(
                url="https://www.theverge.com/ai-artificial-intelligence/928342/openai-daybreak-security-ai",
                title="OpenAI just released its answer to Claude Mythos",
            )
        ],
        category="business",
        subcategory="big_tech",
        reason="[LEAD] Most important business story",
    )

    mock_exa = MagicMock()
    mock_exa.search_and_contents.side_effect = [
        SimpleNamespace(results=[]),
        SimpleNamespace(
            results=[
                SimpleNamespace(
                    url="https://openai.com/daybreak/",
                    title="Daybreak",
                    text="Official OpenAI Daybreak page",
                )
            ]
        ),
    ]
    mock_exa.find_similar_and_contents.return_value = SimpleNamespace(results=[])

    with patch("services.news_collection.settings") as mock_settings, \
         patch.dict("sys.modules", {"exa_py": SimpleNamespace(Exa=lambda api_key: mock_exa)}):
        mock_settings.exa_api_key = "test-key"
        enriched = await enrich_sources(
            [group],
            {group.primary_url: "The Verge coverage"},
            target_date="2026-05-13",
        )

    assert any(source["url"] == "https://openai.com/daybreak/" for source in enriched[group.primary_url])
    first_kwargs = mock_exa.search_and_contents.call_args_list[0].kwargs
    second_kwargs = mock_exa.search_and_contents.call_args_list[1].kwargs
    assert "start_published_date" in first_kwargs
    assert "start_published_date" not in second_kwargs


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


class _FakeCommunityResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class _FakeCommunityClient:
    def __init__(self, *args, mode: str = "empty", **kwargs):
        self.mode = mode

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str, **kwargs):
        params = kwargs.get("params") or {}
        if self.mode == "hn_match" and "hn.algolia.com" in url:
            if params.get("restrictSearchableAttributes") == "url":
                return _FakeCommunityResponse({
                    "hits": [
                        {
                            "objectID": "123",
                            "title": "GPT-5 Released",
                            "points": 42,
                            "num_comments": 8,
                        }
                    ]
                })
            if params.get("tags") == "comment,story_123":
                return _FakeCommunityResponse({
                    "hits": [
                        {
                            "comment_text": (
                                "This is a game changer for teams comparing benchmark "
                                "claims against real deployment constraints."
                            )
                        }
                    ]
                })
        return _FakeCommunityResponse({"hits": [], "data": {"children": []}})


@pytest.mark.asyncio
async def test_collect_community_reactions_returns_text():
    """Community reactions should return combined text."""
    with patch("httpx.AsyncClient", lambda *args, **kwargs: _FakeCommunityClient(mode="hn_match")), \
         patch("services.news_collection.asyncio.sleep", new_callable=AsyncMock), \
         patch("services.news_collection.settings") as mock_settings:
        mock_settings.brave_api_key = ""

        from services.news_collection import collect_community_reactions
        text = await collect_community_reactions("GPT-5 Released", "https://openai.com/gpt5")

    assert "game changer" in text
    assert "Hacker News" in text


@pytest.mark.asyncio
async def test_collect_community_reactions_no_api_key():
    """No community matches returns empty string."""
    with patch("httpx.AsyncClient", lambda *args, **kwargs: _FakeCommunityClient()), \
         patch("services.news_collection.asyncio.sleep", new_callable=AsyncMock), \
         patch("services.news_collection.settings") as mock_settings:
        mock_settings.brave_api_key = ""

        from services.news_collection import collect_community_reactions
        text = await collect_community_reactions("Title", "https://example.com")

    assert text == ""


@pytest.mark.asyncio
async def test_collect_community_reactions_api_error():
    """Community API error returns empty string, not crash."""
    async def failing_get(*args, **kwargs):
        raise TimeoutError("Timeout")

    client = _FakeCommunityClient()
    client.get = failing_get

    with patch("httpx.AsyncClient", lambda *args, **kwargs: client), \
         patch("services.news_collection.asyncio.sleep", new_callable=AsyncMock), \
         patch("services.news_collection.settings") as mock_settings:
        mock_settings.brave_api_key = ""

        from services.news_collection import collect_community_reactions
        text = await collect_community_reactions("Title", "https://example.com")

    assert text == ""


@pytest.mark.asyncio
async def test_collect_community_reactions_client_construction_error():
    """HTTP client construction failure returns empty string, not crash."""
    with patch("httpx.AsyncClient", side_effect=Exception("bad client")), \
         patch("services.news_collection.settings") as mock_settings:
        mock_settings.brave_api_key = ""

        from services.news_collection import collect_community_reactions
        text = await collect_community_reactions("Title", "https://example.com")

    assert text == ""


@pytest.mark.skipif(
    not settings.supabase_url,
    reason="Requires live Supabase connection"
)
def test_load_domain_filters_returns_three_categories():
    """domain filter loader가 3개 카테고리로 분류된 set을 반환한다."""
    from services.news_collection import _load_domain_filters

    # Clear lru_cache in case another test populated it
    _load_domain_filters.cache_clear()
    filters = _load_domain_filters()
    assert "block_non_en" in filters
    assert "official_priority" in filters
    assert "media_tier" in filters
    assert isinstance(filters["block_non_en"], frozenset)
    # Sanity: 시드 데이터가 들어 있어야 함
    assert "openai.com" in filters["official_priority"]
    assert "36kr.com" in filters["block_non_en"]


def test_classify_source_meta_research_blocklist_returns_spam_tier():
    """Domains in research_blocklist should be marked source_kind='spam', source_tier='spam'."""
    from services.news_collection import _classify_source_meta, _load_domain_filters
    _load_domain_filters.cache_clear()
    # Pre-condition: agent-wars.com seeded in research_blocklist (migration 00051)
    result = _classify_source_meta("https://agent-wars.com/some/article", title="x")
    assert result["source_tier"] == "spam"
    assert result["source_kind"] == "spam"
    assert result["source_confidence"] == "low"


def test_classify_source_meta_research_priority_returns_primary_tier():
    """Research priority domains should be marked primary tier with high confidence."""
    from services.news_collection import _classify_source_meta, _load_domain_filters
    _load_domain_filters.cache_clear()
    # Use openreview.net — added in migration 00051, not handled by existing logic
    result = _classify_source_meta("https://openreview.net/forum?id=abc123", title="paper")
    assert result["source_tier"] == "primary"
    assert result["source_confidence"] == "high"

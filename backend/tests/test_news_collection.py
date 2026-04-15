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
    return (
        patch("services.news_collection._collect_exa", new_callable=AsyncMock, return_value=[]),
        patch("services.news_collection._collect_brave", new_callable=AsyncMock, return_value=[]),
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
    p4, p5 = _patch_other_collectors()
    with patch("services.news_collection.TavilyClient", return_value=mock_tavily), \
         patch("services.news_collection.settings") as mock_settings, \
         p1, p2, p3, p4, p5:
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

"""Tests for the current daily pipeline orchestrator."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.news_pipeline import (
    ClassifiedCandidate,
    ClassifiedGroup,
    ClassificationResult,
    CommunityInsight,
    GroupedItem,
    NewsCandidate,
)


SAMPLE_CANDIDATES = [
    NewsCandidate(title="GPT-5", url="https://a.com/1", snippet="Model release", source="tavily"),
    NewsCandidate(title="AI Fund", url="https://b.com/2", snippet="$500M raised", source="tavily"),
]

SAMPLE_COLLECT_META = {
    "is_backfill": False,
    "queries": ["latest AI artificial intelligence news today"],
    "date_kwargs": {"days": 2},
    "total_results": 2,
    "unique_candidates": 2,
}

SAMPLE_CLASSIFY_RESULT = ClassificationResult(
    research_picks=[
        ClassifiedCandidate(
            title="GPT-5",
            url="https://a.com/1",
            snippet="Model release",
            source="tavily",
            category="research",
            subcategory="llm_models",
            relevance_score=0.9,
            reason="Major",
        ),
    ],
    business_picks=[
        ClassifiedCandidate(
            title="AI Fund",
            url="https://b.com/2",
            snippet="$500M raised",
            source="tavily",
            category="business",
            subcategory="industry",
            relevance_score=0.85,
            reason="Big funding",
        ),
    ],
)

SAMPLE_MERGED_RESULT = ClassificationResult(
    research=[
        ClassifiedGroup(
            group_title="GPT-5",
            items=[GroupedItem(url="https://a.com/1", title="GPT-5")],
            category="research",
            subcategory="llm_models",
            relevance_score=0.9,
            reason="Major",
        ),
    ],
    business=[
        ClassifiedGroup(
            group_title="AI Fund",
            items=[GroupedItem(url="https://b.com/2", title="AI Fund")],
            category="business",
            subcategory="industry",
            relevance_score=0.85,
            reason="Big funding",
        ),
    ],
    research_picks=SAMPLE_CLASSIFY_RESULT.research_picks,
    business_picks=SAMPLE_CLASSIFY_RESULT.business_picks,
)

EMPTY_USAGE = {"model_used": "gpt-4o", "input_tokens": 0, "output_tokens": 0, "tokens_used": 0, "cost_usd": 0.0}


class _Query:
    def __init__(self, data):
        self._data = data

    def select(self, *args, **kwargs):
        return self

    def update(self, *args, **kwargs):
        return self

    def insert(self, *args, **kwargs):
        return self

    def upsert(self, *args, **kwargs):
        return self

    def delete(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def gte(self, *args, **kwargs):
        return self

    def in_(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        return MagicMock(data=self._data)


class _Supabase:
    def table(self, name):
        if name == "pipeline_runs":
            return _Query([])
        if name == "news_posts":
            return _Query([])
        if name == "pipeline_logs":
            return _Query([])
        return _Query([])


def _community_summary_map():
    return {
        "https://a.com/1": CommunityInsight(sentiment="positive", quotes=[], quotes_ko=[]),
        "https://b.com/2": CommunityInsight(sentiment="mixed", quotes=[], quotes_ko=[]),
    }


@pytest.mark.asyncio
async def test_run_daily_pipeline_happy_path():
    """Current pipeline creates 4 digest rows when both categories survive."""
    with patch("services.pipeline.get_supabase", return_value=_Supabase()), \
         patch("services.pipeline.collect_news", new_callable=AsyncMock, return_value=(SAMPLE_CANDIDATES, SAMPLE_COLLECT_META)), \
         patch("services.pipeline.classify_candidates", new_callable=AsyncMock, return_value=(SAMPLE_CLASSIFY_RESULT, EMPTY_USAGE, "prompt body")), \
         patch("services.pipeline.merge_classified", new_callable=AsyncMock, return_value=(SAMPLE_MERGED_RESULT, EMPTY_USAGE)), \
         patch("services.pipeline.collect_community_reactions", new_callable=AsyncMock, return_value="community raw"), \
         patch("services.pipeline.summarize_community", new_callable=AsyncMock, return_value=(_community_summary_map(), EMPTY_USAGE)), \
         patch("services.pipeline.rank_classified", new_callable=AsyncMock, side_effect=[(SAMPLE_MERGED_RESULT.research, EMPTY_USAGE), (SAMPLE_MERGED_RESULT.business, EMPTY_USAGE)]), \
         patch("services.pipeline.enrich_sources", new_callable=AsyncMock, return_value={}), \
         patch("services.pipeline._fetch_handbook_slugs", return_value=[]), \
         patch("services.pipeline._generate_digest", new_callable=AsyncMock, return_value=(2, [], EMPTY_USAGE)):
        from services.pipeline import run_daily_pipeline

        result = await run_daily_pipeline()

    assert result.posts_created == 4
    assert result.errors == []
    assert result.batch_id


@pytest.mark.asyncio
async def test_pipeline_no_research_creates_2_posts():
    """When only business survives after classify, only the business digest is created."""
    classification_no_research = ClassificationResult(
        business_picks=SAMPLE_CLASSIFY_RESULT.business_picks,
    )
    merged_no_research = ClassificationResult(
        business=SAMPLE_MERGED_RESULT.business,
        business_picks=SAMPLE_CLASSIFY_RESULT.business_picks,
    )

    with patch("services.pipeline.get_supabase", return_value=_Supabase()), \
         patch("services.pipeline.collect_news", new_callable=AsyncMock, return_value=(SAMPLE_CANDIDATES, SAMPLE_COLLECT_META)), \
         patch("services.pipeline.classify_candidates", new_callable=AsyncMock, return_value=(classification_no_research, EMPTY_USAGE, "prompt body")), \
         patch("services.pipeline.merge_classified", new_callable=AsyncMock, return_value=(merged_no_research, EMPTY_USAGE)), \
         patch("services.pipeline.collect_community_reactions", new_callable=AsyncMock, return_value="community raw"), \
         patch("services.pipeline.summarize_community", new_callable=AsyncMock, return_value=(_community_summary_map(), EMPTY_USAGE)), \
         patch("services.pipeline.rank_classified", new_callable=AsyncMock, side_effect=[([], EMPTY_USAGE), (merged_no_research.business, EMPTY_USAGE)]), \
         patch("services.pipeline.enrich_sources", new_callable=AsyncMock, return_value={}), \
         patch("services.pipeline._fetch_handbook_slugs", return_value=[]), \
         patch("services.pipeline._generate_digest", new_callable=AsyncMock, return_value=(2, [], EMPTY_USAGE)):
        from services.pipeline import run_daily_pipeline

        result = await run_daily_pipeline()

    assert result.posts_created == 2


@pytest.mark.asyncio
async def test_pipeline_no_candidates_returns_zero_posts():
    """Empty collect result returns 0 posts without error."""
    with patch("services.pipeline.get_supabase", return_value=_Supabase()), \
         patch("services.pipeline.collect_news", new_callable=AsyncMock, return_value=([], {})):
        from services.pipeline import run_daily_pipeline

        result = await run_daily_pipeline()

    assert result.posts_created == 0
    assert result.errors == []


@pytest.mark.asyncio
async def test_pipeline_digest_failure_continues():
    """Digest generation failure for one category should not stop the other."""
    with patch("services.pipeline.get_supabase", return_value=_Supabase()), \
         patch("services.pipeline.collect_news", new_callable=AsyncMock, return_value=(SAMPLE_CANDIDATES, SAMPLE_COLLECT_META)), \
         patch("services.pipeline.classify_candidates", new_callable=AsyncMock, return_value=(SAMPLE_CLASSIFY_RESULT, EMPTY_USAGE, "prompt body")), \
         patch("services.pipeline.merge_classified", new_callable=AsyncMock, return_value=(SAMPLE_MERGED_RESULT, EMPTY_USAGE)), \
         patch("services.pipeline.collect_community_reactions", new_callable=AsyncMock, return_value="community raw"), \
         patch("services.pipeline.summarize_community", new_callable=AsyncMock, return_value=(_community_summary_map(), EMPTY_USAGE)), \
         patch("services.pipeline.rank_classified", new_callable=AsyncMock, side_effect=[(SAMPLE_MERGED_RESULT.research, EMPTY_USAGE), (SAMPLE_MERGED_RESULT.business, EMPTY_USAGE)]), \
         patch("services.pipeline.enrich_sources", new_callable=AsyncMock, return_value={}), \
         patch("services.pipeline._fetch_handbook_slugs", return_value=[]), \
         patch("services.pipeline._generate_digest", new_callable=AsyncMock, side_effect=[Exception("digest failed"), (2, [], EMPTY_USAGE)]):
        from services.pipeline import run_daily_pipeline

        result = await run_daily_pipeline()

    assert result.posts_created == 2
    assert any("Digest generation failed" in error for error in result.errors)


@pytest.mark.asyncio
async def test_pipeline_supabase_not_configured():
    """Pipeline without Supabase should fail gracefully."""
    with patch("services.pipeline.get_supabase", return_value=None):
        from services.pipeline import run_daily_pipeline

        result = await run_daily_pipeline()

    assert result.posts_created == 0
    assert any("not configured" in e.lower() for e in result.errors)

"""Tests for the pipeline orchestrator."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.news_pipeline import (
    FactPack,
    NewsCandidate,
    PersonaOutput,
    RankedCandidate,
    RankingResult,
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

SAMPLE_RANKING = RankingResult(
    research=RankedCandidate(
        title="GPT-5", url="https://a.com/1", snippet="Model release",
        source="tavily", assigned_type="research", relevance_score=0.9, ranking_reason="Major release",
    ),
    business=RankedCandidate(
        title="AI Fund", url="https://b.com/2", snippet="$500M raised",
        source="tavily", assigned_type="business", relevance_score=0.85, ranking_reason="Big funding",
    ),
)

SAMPLE_FACT_PACK = FactPack.model_validate({
    "headline": "GPT-5 Released",
    "key_facts": [{"id": "f1", "claim": "Test", "why_it_matters": "Test", "source_ids": ["s1"], "confidence": "high"}],
    "numbers": [], "entities": [],
    "sources": [{"id": "s1", "title": "Test", "publisher": "test.com", "url": "https://test.com", "published_at": "2026-03-15"}],
    "community_summary": "Positive reactions.",
})

SAMPLE_PERSONA = PersonaOutput(en="Expert EN content " + "x" * 3000, ko="Expert KO content " + "가" * 3000)

EMPTY_USAGE = {"model_used": "gpt-4o", "input_tokens": 0, "output_tokens": 0, "tokens_used": 0, "cost_usd": 0.0}


def _mock_supabase():
    """Create a mock Supabase client with chain methods."""
    mock = MagicMock()
    mock.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[
        {"slug": "transformer"}, {"slug": "llm"}, {"slug": "gpt"},
    ])
    mock.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "run-id"}])
    mock.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    mock.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[{"id": "post-id"}])
    return mock


@pytest.mark.asyncio
async def test_run_daily_pipeline_happy_path():
    """Full pipeline creates 4 post rows (2 types x 2 locales)."""
    mock_sb = _mock_supabase()

    with patch("services.pipeline.get_supabase", return_value=mock_sb), \
         patch("services.pipeline.collect_news", new_callable=AsyncMock, return_value=(SAMPLE_CANDIDATES, SAMPLE_COLLECT_META)), \
         patch("services.pipeline.rank_candidates", new_callable=AsyncMock, return_value=(SAMPLE_RANKING, EMPTY_USAGE)), \
         patch("services.pipeline.collect_community_reactions", new_callable=AsyncMock, return_value="Reactions text"), \
         patch("services.pipeline.extract_facts", new_callable=AsyncMock, return_value=(SAMPLE_FACT_PACK, EMPTY_USAGE)), \
         patch("services.pipeline.write_persona", new_callable=AsyncMock, return_value=(SAMPLE_PERSONA, EMPTY_USAGE)):

        from services.pipeline import run_daily_pipeline
        result = await run_daily_pipeline()

    assert result.posts_created == 4  # research EN/KO + business EN/KO
    assert result.errors == []
    assert result.batch_id  # non-empty


@pytest.mark.asyncio
async def test_pipeline_no_research_creates_2_posts():
    """When ranking returns no research, only business posts are created."""
    ranking_no_research = RankingResult(
        research=None,
        business=SAMPLE_RANKING.business,
    )
    mock_sb = _mock_supabase()

    with patch("services.pipeline.get_supabase", return_value=mock_sb), \
         patch("services.pipeline.collect_news", new_callable=AsyncMock, return_value=(SAMPLE_CANDIDATES, SAMPLE_COLLECT_META)), \
         patch("services.pipeline.rank_candidates", new_callable=AsyncMock, return_value=(ranking_no_research, EMPTY_USAGE)), \
         patch("services.pipeline.collect_community_reactions", new_callable=AsyncMock, return_value="Reactions"), \
         patch("services.pipeline.extract_facts", new_callable=AsyncMock, return_value=(SAMPLE_FACT_PACK, EMPTY_USAGE)), \
         patch("services.pipeline.write_persona", new_callable=AsyncMock, return_value=(SAMPLE_PERSONA, EMPTY_USAGE)):

        from services.pipeline import run_daily_pipeline
        result = await run_daily_pipeline()

    assert result.posts_created == 2  # business EN + KO only


@pytest.mark.asyncio
async def test_pipeline_no_candidates_returns_zero_posts():
    """Empty Tavily results = 0 posts, no error."""
    mock_sb = _mock_supabase()

    with patch("services.pipeline.get_supabase", return_value=mock_sb), \
         patch("services.pipeline.collect_news", new_callable=AsyncMock, return_value=([], {})):

        from services.pipeline import run_daily_pipeline
        result = await run_daily_pipeline()

    assert result.posts_created == 0
    assert result.errors == []
    # pipeline_runs should be updated to "success", not left "running"
    mock_sb.table.return_value.update.assert_called()


@pytest.mark.asyncio
async def test_pipeline_fact_extraction_failure_continues():
    """Fact extraction failure for one post type doesn't stop the other."""
    mock_sb = _mock_supabase()

    call_count = {"extract": 0}

    async def _mock_extract(*args, **kwargs):
        call_count["extract"] += 1
        if call_count["extract"] == 1:
            raise Exception("API timeout")
        return SAMPLE_FACT_PACK, EMPTY_USAGE

    with patch("services.pipeline.get_supabase", return_value=mock_sb), \
         patch("services.pipeline.collect_news", new_callable=AsyncMock, return_value=(SAMPLE_CANDIDATES, SAMPLE_COLLECT_META)), \
         patch("services.pipeline.rank_candidates", new_callable=AsyncMock, return_value=(SAMPLE_RANKING, EMPTY_USAGE)), \
         patch("services.pipeline.collect_community_reactions", new_callable=AsyncMock, return_value="Reactions"), \
         patch("services.pipeline.extract_facts", side_effect=_mock_extract), \
         patch("services.pipeline.write_persona", new_callable=AsyncMock, return_value=(SAMPLE_PERSONA, EMPTY_USAGE)):

        from services.pipeline import run_daily_pipeline
        result = await run_daily_pipeline()

    assert result.posts_created == 2  # only one post type (EN + KO)
    assert len(result.errors) == 1


@pytest.mark.asyncio
async def test_pipeline_supabase_not_configured():
    """Pipeline without Supabase should fail gracefully."""
    with patch("services.pipeline.get_supabase", return_value=None):

        from services.pipeline import run_daily_pipeline
        result = await run_daily_pipeline()

    assert result.posts_created == 0
    assert any("not configured" in e.lower() for e in result.errors)

"""Tests for the pipeline orchestrator."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.news_pipeline import (
    ClassifiedCandidate,
    ClassificationResult,
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

SAMPLE_CLASSIFICATION = ClassificationResult(
    research=[
        ClassifiedCandidate(
            title="GPT-5", url="https://a.com/1", snippet="Model release",
            category="research", subcategory="llm_models", relevance_score=0.9, reason="Major",
        ),
    ],
    business=[
        ClassifiedCandidate(
            title="AI Fund", url="https://b.com/2", snippet="$500M raised",
            category="business", subcategory="industry", relevance_score=0.85, reason="Big funding",
        ),
    ],
)

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
    mock.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    return mock


def _mock_openai_digest_response():
    """Mock OpenAI response for digest generation."""
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = json.dumps({
        "en": "## One-Line Summary\nTest digest EN content " + "x" * 500,
        "ko": "## 한 줄 요약\nTest digest KO content " + "가" * 500,
    })
    mock_resp.usage = MagicMock()
    mock_resp.usage.prompt_tokens = 2000
    mock_resp.usage.completion_tokens = 1000
    mock_resp.usage.total_tokens = 3000
    return mock_resp


@pytest.mark.asyncio
async def test_run_daily_pipeline_happy_path():
    """Full v3 pipeline creates 4 digest rows (2 types x 2 locales)."""
    mock_sb = _mock_supabase()
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_digest_response()

    with patch("services.pipeline.get_supabase", return_value=mock_sb), \
         patch("services.pipeline.collect_news", new_callable=AsyncMock, return_value=(SAMPLE_CANDIDATES, SAMPLE_COLLECT_META)), \
         patch("services.pipeline.classify_candidates", new_callable=AsyncMock, return_value=(SAMPLE_CLASSIFICATION, EMPTY_USAGE)), \
         patch("services.pipeline.get_openai_client", return_value=mock_client):

        from services.pipeline import run_daily_pipeline
        result = await run_daily_pipeline()

    assert result.posts_created == 4  # research EN/KO + business EN/KO
    assert result.errors == []
    assert result.batch_id


@pytest.mark.asyncio
async def test_pipeline_no_research_creates_2_posts():
    """When classification returns no research, only business digest is created."""
    classification_no_research = ClassificationResult(
        research=[],
        business=SAMPLE_CLASSIFICATION.business,
    )
    mock_sb = _mock_supabase()
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_digest_response()

    with patch("services.pipeline.get_supabase", return_value=mock_sb), \
         patch("services.pipeline.collect_news", new_callable=AsyncMock, return_value=(SAMPLE_CANDIDATES, SAMPLE_COLLECT_META)), \
         patch("services.pipeline.classify_candidates", new_callable=AsyncMock, return_value=(classification_no_research, EMPTY_USAGE)), \
         patch("services.pipeline.get_openai_client", return_value=mock_client):

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
    mock_sb.table.return_value.update.assert_called()


@pytest.mark.asyncio
async def test_pipeline_digest_failure_continues():
    """Digest generation failure for one type doesn't stop the other."""
    mock_sb = _mock_supabase()
    mock_client = AsyncMock()

    call_count = {"calls": 0}

    async def _mock_create(**kwargs):
        call_count["calls"] += 1
        # First 4 calls fail (research: 2 personas × 2 attempts each with retry)
        if call_count["calls"] <= 4:
            raise Exception("API timeout")
        return _mock_openai_digest_response()

    mock_client.chat.completions.create.side_effect = _mock_create

    with patch("services.pipeline.get_supabase", return_value=mock_sb), \
         patch("services.pipeline.collect_news", new_callable=AsyncMock, return_value=(SAMPLE_CANDIDATES, SAMPLE_COLLECT_META)), \
         patch("services.pipeline.classify_candidates", new_callable=AsyncMock, return_value=(SAMPLE_CLASSIFICATION, EMPTY_USAGE)), \
         patch("services.pipeline.get_openai_client", return_value=mock_client):

        from services.pipeline import run_daily_pipeline
        result = await run_daily_pipeline()

    # Research digest: both personas failed → not saved (requires both)
    # Business digest: both personas succeeded → saved (EN + KO)
    assert result.posts_created == 2  # only business succeeded (EN + KO)
    assert len(result.errors) >= 2  # 2 research persona failures + incomplete error


@pytest.mark.asyncio
async def test_pipeline_supabase_not_configured():
    """Pipeline without Supabase should fail gracefully."""
    with patch("services.pipeline.get_supabase", return_value=None):

        from services.pipeline import run_daily_pipeline
        result = await run_daily_pipeline()

    assert result.posts_created == 0
    assert any("not configured" in e.lower() for e in result.errors)

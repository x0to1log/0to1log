from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.ranking import NewsCandidate, NewsRankingResult, RankedCandidate
from models.research import ResearchPost


def _make_supabase_mock():
    mock = MagicMock()
    chain = mock.table.return_value
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.maybe_single.return_value = chain
    chain.execute.return_value = MagicMock(data=[])
    return mock


def test_should_skip_research_candidate_when_score_below_threshold():
    from services.pipeline import _should_skip_research_candidate

    candidate = RankedCandidate(
        title="Incremental model tuning update",
        url="https://example.com/update",
        snippet="Minor tuning changes.",
        source="tavily",
        assigned_type="research",
        relevance_score=0.84,
        ranking_reason="Small update",
    )

    assert _should_skip_research_candidate(candidate, None) is True


def test_should_skip_research_candidate_when_same_url_as_latest_post():
    from services.pipeline import _should_skip_research_candidate

    candidate = RankedCandidate(
        title="OpenAI ships GPT-5 reasoning update",
        url="https://openai.com/blog/gpt-5",
        snippet="Fresh update.",
        source="tavily",
        assigned_type="research",
        relevance_score=0.92,
        ranking_reason="Same story",
    )
    latest_post = {
        "title": "OpenAI ships GPT-5 reasoning update",
        "url": "https://openai.com/blog/gpt-5",
    }

    assert _should_skip_research_candidate(candidate, latest_post) is True


def test_should_keep_research_candidate_for_very_high_score_on_different_url():
    from services.pipeline import _should_skip_research_candidate

    candidate = RankedCandidate(
        title="OpenAI ships GPT-5 reasoning update for API teams",
        url="https://openai.com/blog/gpt-5-api-update",
        snippet="Substantive new release details.",
        source="tavily",
        assigned_type="research",
        relevance_score=0.96,
        ranking_reason="New high-signal details",
    )
    latest_post = {
        "title": "OpenAI ships GPT-5 reasoning update",
        "url": "https://openai.com/blog/gpt-5",
    }

    assert _should_skip_research_candidate(candidate, latest_post) is False


@pytest.mark.asyncio
async def test_run_daily_pipeline_demotes_research_pick_before_generation():
    from services.pipeline import run_daily_pipeline

    candidate = RankedCandidate(
        title="Incremental model tuning update",
        url="https://example.com/update",
        snippet="Small change to an existing model rollout.",
        source="tavily",
        assigned_type="research",
        relevance_score=0.84,
        ranking_reason="Not a strong enough daily research signal",
    )
    research_no_news = ResearchPost(
        has_news=False,
        title="No sufficiently distinct AI research updates today",
        slug="2026-03-12-research-daily",
        no_news_notice="No sufficiently distinct AI research or model updates were confirmed in the past 24 hours.",
        recent_fallback="Yesterday's major themes still dominated today's signals.",
        source_urls=[],
        news_temperature=1,
        tags=["no-news"],
    )
    ko_no_news = {
        "has_news": False,
        "title": "오늘은 충분히 다른 AI 리서치 업데이트가 없었습니다",
        "slug": "2026-03-12-research-daily",
        "no_news_notice": "지난 24시간 동안 어제와 충분히 다른 실질적 AI 연구 업데이트는 확인되지 않았습니다.",
        "recent_fallback": "어제 다룬 주요 흐름이 오늘 신호에서도 크게 반복되었습니다.",
        "source_urls": [],
        "news_temperature": 1,
        "tags": ["no-news"],
        "focus_items": [],
    }
    mock_db = _make_supabase_mock()

    with (
        patch("services.pipeline.acquire_pipeline_lock", AsyncMock(return_value="run-1")),
        patch("services.pipeline.collect_all_news", AsyncMock(return_value=[
            NewsCandidate(
                title="Incremental model tuning update",
                url="https://example.com/update",
                snippet="Small change to an existing model rollout.",
                source="tavily",
            )
        ])),
        patch("services.pipeline.rank_candidates", AsyncMock(return_value=NewsRankingResult(
            research_pick=candidate,
            business_main_pick=None,
            related_picks=None,
        ))),
        patch("services.pipeline.get_supabase", return_value=mock_db),
        patch("services.pipeline._save_candidates"),
        patch("services.pipeline.generate_research_post", AsyncMock(return_value=research_no_news)) as mock_generate_research,
        patch("services.pipeline.translate_post", AsyncMock(return_value=ko_no_news)),
        patch("services.pipeline._save_research_post", MagicMock(return_value=("post-id", "tg-id"))),
        patch("services.pipeline._extract_and_create_terms", AsyncMock()),
        patch("services.pipeline.release_pipeline_lock", AsyncMock()) as mock_release,
    ):
        await run_daily_pipeline("2026-03-12")

    assert mock_generate_research.await_args.args[0] is None
    mock_release.assert_awaited_once_with("run-1", "success")

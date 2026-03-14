from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.ranking import NewsCandidate, NewsRankingResult, RankedCandidate, RelatedPicks
from models.research import ResearchPost


def _make_supabase_mock():
    mock = MagicMock()
    chain = mock.table.return_value
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.maybe_single.return_value = chain
    chain.insert.return_value = chain
    chain.update.return_value = chain
    chain.execute.return_value = MagicMock(data=[])
    return mock


def _saved_business_row() -> dict:
    return {
        "id": "business-en-id",
        "title": "Anthropic funding changes enterprise AI positioning",
        "slug": "2026-03-12-business-daily",
        "locale": "en",
        "content_analysis": "## Core Analysis\n" + ("Shared analysis. " * 200),
        "content_beginner": "## The Story\n" + ("Beginner insight. " * 260),
        "content_learner": "## What Happened\n" + ("Learner insight. " * 260),
        "content_expert": "## Executive Summary\n" + ("Expert insight. " * 260),
        "fact_pack": {
            "key_facts": ["Anthropic raised new capital."],
            "numbers": ["Funding amount not disclosed."],
            "entities": ["Anthropic", "Enterprise AI"],
            "timeline": ["2026-Q1 — Funding round announced."],
        },
        "source_cards": [
            {
                "id": "src-1",
                "title": "Anthropic funding update",
                "publisher": "Anthropic",
                "url": "https://anthropic.com/news/example",
                "published_at": "2026-03-12T00:00:00Z",
                "evidence_snippet": "Official funding statement.",
                "claim_ids": ["claim-1"],
            }
        ],
        "guide_items": {
            "one_liner": "Anthropic raised new capital.",
            "action_item": "Review vendor exposure.",
            "critical_gotcha": "Capital does not guarantee execution.",
            "rotating_item": "Balance-sheet strength matters to buyers.",
            "quiz_poll": {
                "question": "What changes first after a major raise?",
                "options": ["Compute", "Color", "Logo"],
                "answer": "Compute",
                "explanation": "Compute and hiring usually move first.",
            },
        },
        "related_news": {
            "big_tech": None,
            "industry_biz": None,
            "new_tools": None,
        },
        "source_urls": ["https://anthropic.com/news/example"],
        "news_temperature": 4,
        "tags": ["anthropic"],
        "excerpt": "Anthropic's funding changes vendor durability assumptions.",
        "focus_items": [
            "Capital affects enterprise trust.",
            "Funding can expand compute access.",
            "Execution still matters.",
        ],
        "translation_group_id": "tg-business",
    }


def _saved_research_row() -> dict:
    return {
        "id": "research-en-id",
        "title": "GPT-5 latency update",
        "slug": "2026-03-12-research-daily",
        "locale": "en",
        "content_original": "## 1. What Happened\n" + ("Research context. " * 260),
        "no_news_notice": None,
        "recent_fallback": None,
        "guide_items": {
            "one_liner": "Latency improved.",
            "action_item": "Benchmark again.",
            "critical_gotcha": "Latency does not equal lower cost.",
            "rotating_item": "Watch production stability.",
            "quiz_poll": {
                "question": "What should teams validate first?",
                "options": ["Reliability", "Mascot", "Color"],
                "answer": "Reliability",
                "explanation": "Reliability has to come first.",
            },
        },
        "source_cards": [
            {
                "id": "src-1",
                "title": "GPT-5 release notes",
                "publisher": "OpenAI",
                "url": "https://openai.com/blog/gpt-5",
                "published_at": "2026-03-12T00:00:00Z",
                "evidence_snippet": "Official release note.",
                "claim_ids": ["claim-1"],
            }
        ],
        "source_urls": ["https://openai.com/blog/gpt-5"],
        "news_temperature": 5,
        "tags": ["gpt-5"],
        "excerpt": "Latency changed enough to matter for UX.",
        "focus_items": [
            "Latency improved.",
            "UX implications matter.",
            "Benchmark in production.",
        ],
        "translation_group_id": "tg-research",
    }


def _saved_ranked_candidates() -> list[dict]:
    return [
        {
            "title": "GPT-5 update",
            "url": "https://openai.com/blog/gpt-5",
            "snippet": "Latency improvements.",
            "source": "tavily",
            "assigned_type": "research",
            "relevance_score": 0.93,
            "ranking_reason": "Clear model update with production impact",
        },
        {
            "title": "Anthropic raises funding",
            "url": "https://anthropic.com/news/example",
            "snippet": "Anthropic secured another major funding round.",
            "source": "tavily",
            "assigned_type": "business_main",
            "relevance_score": 0.91,
            "ranking_reason": "Large funding round with enterprise AI implications",
        },
        {
            "title": "OpenAI expands bundles",
            "url": "https://openai.com/blog/bundles",
            "snippet": "Enterprise bundles widened.",
            "source": "tavily",
            "assigned_type": "industry_biz",
            "relevance_score": 0.71,
            "ranking_reason": "Useful related enterprise context",
        },
    ]


def _no_news_research_post() -> ResearchPost:
    return ResearchPost(
        has_news=False,
        title="No sufficiently distinct AI research updates today",
        slug="2026-03-12-research-daily",
        no_news_notice="No sufficiently distinct AI research or model updates were confirmed in the past 24 hours.",
        recent_fallback="Yesterday's major themes still dominated today's signals.",
        source_urls=[],
        news_temperature=1,
        tags=["no-news"],
    )


def _ko_no_news_research_payload() -> dict:
    return {
        "has_news": False,
        "title": "오늘은 충분히 다른 AI 연구 업데이트가 없었습니다.",
        "slug": "2026-03-12-research-daily",
        "no_news_notice": "오늘은 충분히 다른 AI 연구 업데이트가 없었습니다.",
        "recent_fallback": "어제의 주요 흐름이 계속 이어졌습니다.",
        "source_urls": [],
        "news_temperature": 1,
        "tags": ["no-news"],
        "focus_items": [],
    }


def test_ranking_snapshot_rebuild_restores_research_business_and_related_picks():
    from services.pipeline import _ranking_from_saved_candidates

    ranking = _ranking_from_saved_candidates(_saved_ranked_candidates())

    assert ranking.research_pick is not None
    assert ranking.research_pick.url == "https://openai.com/blog/gpt-5"
    assert ranking.business_main_pick is not None
    assert ranking.business_main_pick.url == "https://anthropic.com/news/example"
    assert ranking.related_picks is not None
    assert ranking.related_picks.industry_biz is not None
    assert ranking.related_picks.industry_biz.url == "https://openai.com/blog/bundles"


@pytest.mark.asyncio
async def test_run_daily_pipeline_reuses_existing_business_en_when_only_ko_is_missing():
    from services.pipeline import run_daily_pipeline

    candidate = RankedCandidate(
        title="Anthropic raises funding",
        url="https://anthropic.com/news/example",
        snippet="Anthropic secured another major funding round.",
        source="tavily",
        assigned_type="business_main",
        relevance_score=0.91,
        ranking_reason="Large funding round with enterprise AI implications",
    )
    research_post = ResearchPost(
        has_news=False,
        title="No sufficiently distinct AI research updates today",
        slug="2026-03-12-research-daily",
        no_news_notice="No sufficiently distinct AI research or model updates were confirmed in the past 24 hours.",
        recent_fallback="Yesterday's major themes still dominated today's signals.",
        source_urls=[],
        news_temperature=1,
        tags=["no-news"],
    )
    ko_research = {
        "has_news": False,
        "title": "오늘은 충분히 다른 AI 연구 업데이트가 없었습니다",
        "slug": "2026-03-12-research-daily",
        "no_news_notice": "오늘은 충분히 다른 AI 연구 업데이트가 없었습니다.",
        "recent_fallback": "어제의 흐름이 그대로 이어졌습니다.",
        "source_urls": [],
        "news_temperature": 1,
        "tags": ["no-news"],
        "focus_items": [],
    }
    ko_business = _saved_business_row() | {
        "title": "Anthropic 투자 유치가 엔터프라이즈 AI 포지셔닝을 바꿉니다",
        "slug": "2026-03-12-business-daily",
        "locale": "ko",
    }

    with (
        patch("services.pipeline.acquire_pipeline_lock", AsyncMock(return_value="run-1")),
        patch("services.pipeline.collect_all_news", AsyncMock(return_value=[
            NewsCandidate(
                title="Anthropic raises funding",
                url="https://anthropic.com/news/example",
                snippet="Anthropic secured another major funding round.",
                source="tavily",
            )
        ])),
        patch("services.pipeline.rank_candidates", AsyncMock(return_value=NewsRankingResult(
            research_pick=None,
            business_main_pick=candidate,
            related_picks=RelatedPicks(),
        ))),
        patch("services.pipeline._apply_research_novelty_gate", return_value=(None, {"skip": True, "reason": "missing_candidate"})),
        patch("services.pipeline._save_candidates"),
        patch("services.pipeline.generate_research_post", AsyncMock(return_value=research_post)),
        patch("services.pipeline.translate_post", AsyncMock(side_effect=[(ko_research, {}), (ko_business, {})])) as mock_translate,
        patch("services.pipeline._save_research_post", MagicMock(return_value=("research-en-id", "tg-research"))),
        patch("services.pipeline._save_business_post", MagicMock(return_value=("business-ko-id", "tg-business"))) as mock_save_business,
        patch("services.pipeline._extract_and_create_terms", AsyncMock()),
        patch("services.pipeline.release_pipeline_lock", AsyncMock()) as mock_release,
        patch("services.pipeline._get_saved_post_row", side_effect=lambda batch_id, post_type, locale: (
            _saved_business_row() if (post_type, locale) == ("business", "en") else None
        )),
        patch("services.pipeline.generate_business_post", AsyncMock()) as mock_generate_business,
        patch("services.pipeline.get_supabase", return_value=_make_supabase_mock()),
    ):
        await run_daily_pipeline("2026-03-12")

    mock_generate_business.assert_not_awaited()
    assert mock_translate.await_count == 2
    translated_business_payload = mock_translate.await_args_list[1].args[0]
    assert translated_business_payload["content_analysis"] == _saved_business_row()["content_analysis"]
    assert mock_save_business.call_args.kwargs["source_post_id"] == "business-en-id"
    mock_release.assert_awaited_once_with("run-1", "success")


@pytest.mark.asyncio
async def test_run_daily_pipeline_reuses_existing_research_en_when_only_ko_is_missing():
    from services.pipeline import run_daily_pipeline

    ko_research = _saved_research_row() | {
        "title": "GPT-5 지연 시간 업데이트",
        "slug": "2026-03-12-research-daily",
        "locale": "ko",
    }

    with (
        patch("services.pipeline.acquire_pipeline_lock", AsyncMock(return_value="run-1")),
        patch("services.pipeline.collect_all_news", AsyncMock(return_value=[
            NewsCandidate(
                title="GPT-5 update",
                url="https://openai.com/blog/gpt-5",
                snippet="Latency improvements.",
                source="tavily",
            )
        ])),
        patch("services.pipeline.rank_candidates", AsyncMock(return_value=NewsRankingResult(
            research_pick=None,
            business_main_pick=None,
            related_picks=None,
        ))),
        patch("services.pipeline._apply_research_novelty_gate", return_value=(None, {"skip": True, "reason": "missing_candidate"})),
        patch("services.pipeline._save_candidates"),
        patch("services.pipeline._save_research_post", MagicMock(return_value=("research-ko-id", "tg-research"))),
        patch("services.pipeline.translate_post", AsyncMock(return_value=(ko_research, {}))) as mock_translate,
        patch("services.pipeline._extract_and_create_terms", AsyncMock()),
        patch("services.pipeline.release_pipeline_lock", AsyncMock()) as mock_release,
        patch("services.pipeline._get_saved_post_row", side_effect=lambda batch_id, post_type, locale: (
            _saved_research_row() if (post_type, locale) == ("research", "en") else None
        )),
        patch("services.pipeline.generate_research_post", AsyncMock()) as mock_generate_research,
        patch("services.pipeline.get_supabase", return_value=_make_supabase_mock()),
    ):
        await run_daily_pipeline("2026-03-12")

    mock_generate_research.assert_not_awaited()
    mock_translate.assert_awaited_once()
    translated_research_payload = mock_translate.await_args.args[0]
    assert translated_research_payload["content_original"] == _saved_research_row()["content_original"]
    mock_release.assert_awaited_once_with("run-1", "success")


@pytest.mark.asyncio
async def test_run_daily_pipeline_resume_mode_skips_collect_and_rank_when_snapshot_exists():
    from services.pipeline import run_daily_pipeline

    ranking = NewsRankingResult(
        research_pick=RankedCandidate(**_saved_ranked_candidates()[0]),
        business_main_pick=None,
        related_picks=RelatedPicks(),
    )
    saved_candidates = [
        NewsCandidate(
            title=row["title"],
            url=row["url"],
            snippet=row["snippet"],
            source=row["source"],
        )
        for row in _saved_ranked_candidates()
    ]

    with (
        patch("services.pipeline.acquire_pipeline_lock", AsyncMock(return_value="run-1")),
        patch("services.pipeline._load_saved_ranking_snapshot", return_value=(saved_candidates, ranking), create=True),
        patch("services.pipeline.collect_all_news", AsyncMock()) as mock_collect,
        patch("services.pipeline.rank_candidates", AsyncMock()) as mock_rank,
        patch("services.pipeline._apply_research_novelty_gate", return_value=(None, {"skip": True, "reason": "missing_candidate"})),
        patch("services.pipeline._save_candidates"),
        patch("services.pipeline.generate_research_post", AsyncMock(return_value=_no_news_research_post())),
        patch("services.pipeline.translate_post", AsyncMock(return_value=(_ko_no_news_research_payload(), {}))),
        patch("services.pipeline._save_research_post", MagicMock(return_value=("research-ko-id", "tg-research"))),
        patch("services.pipeline._extract_and_create_terms", AsyncMock()),
        patch("services.pipeline.release_pipeline_lock", AsyncMock()) as mock_release,
        patch("services.pipeline.get_supabase", return_value=_make_supabase_mock()),
    ):
        await run_daily_pipeline("2026-03-12", mode="resume")

    mock_collect.assert_not_awaited()
    mock_rank.assert_not_awaited()
    mock_release.assert_awaited_once_with("run-1", "success")


@pytest.mark.asyncio
async def test_run_daily_pipeline_force_refresh_recollects_even_if_snapshot_exists():
    from services.pipeline import run_daily_pipeline

    ranking = NewsRankingResult(
        research_pick=None,
        business_main_pick=None,
        related_picks=RelatedPicks(),
    )
    collected = [
        NewsCandidate(
            title="GPT-5 update",
            url="https://openai.com/blog/gpt-5",
            snippet="Latency improvements.",
            source="tavily",
        )
    ]
    saved_candidates = [
        NewsCandidate(
            title=row["title"],
            url=row["url"],
            snippet=row["snippet"],
            source=row["source"],
        )
        for row in _saved_ranked_candidates()
    ]

    with (
        patch("services.pipeline.acquire_pipeline_lock", AsyncMock(return_value="run-1")),
        patch("services.pipeline._load_saved_ranking_snapshot", return_value=(saved_candidates, ranking), create=True),
        patch("services.pipeline.collect_all_news", AsyncMock(return_value=collected)) as mock_collect,
        patch("services.pipeline.rank_candidates", AsyncMock(return_value=ranking)) as mock_rank,
        patch("services.pipeline._apply_research_novelty_gate", return_value=(None, {"skip": True, "reason": "missing_candidate"})),
        patch("services.pipeline._save_candidates"),
        patch("services.pipeline.generate_research_post", AsyncMock(return_value=_no_news_research_post())),
        patch("services.pipeline.translate_post", AsyncMock(return_value=(_ko_no_news_research_payload(), {}))),
        patch("services.pipeline._save_research_post", MagicMock(return_value=("research-ko-id", "tg-research"))),
        patch("services.pipeline._extract_and_create_terms", AsyncMock()),
        patch("services.pipeline.release_pipeline_lock", AsyncMock()) as mock_release,
        patch("services.pipeline.get_supabase", return_value=_make_supabase_mock()),
    ):
        await run_daily_pipeline("2026-03-12", mode="force_refresh")

    mock_collect.assert_awaited_once()
    mock_rank.assert_awaited_once()
    mock_release.assert_awaited_once_with("run-1", "success")

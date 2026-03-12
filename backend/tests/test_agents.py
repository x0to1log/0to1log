"""Tests for AI agents with network-blocking mock fixtures.

All external API calls (OpenAI) are mocked. Any real network call will raise.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.ranking import NewsCandidate, NewsRankingResult, RankedCandidate, RelatedPicks
from models.research import ResearchPost
from models.business import BusinessPost


# ---------------------------------------------------------------------------
# Fixtures: block all real network calls
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    """Block any real HTTP calls. Tests must use mocks."""
    import httpx

    def _blocked(*args, **kwargs):
        raise RuntimeError("Real network call blocked in tests!")

    monkeypatch.setattr(httpx.AsyncClient, "send", _blocked)
    monkeypatch.setattr(httpx.Client, "send", _blocked)


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

SAMPLE_CANDIDATES = [
    NewsCandidate(
        title="GPT-5 Released with 10x Speed",
        url="https://openai.com/blog/gpt-5",
        snippet="OpenAI releases GPT-5 with massive performance improvements",
        source="tavily",
    ),
    NewsCandidate(
        title="Anthropic Raises $5B Series D",
        url="https://anthropic.com/news/series-d",
        snippet="Anthropic secures major funding round for AI safety research",
        source="tavily",
    ),
    NewsCandidate(
        title="New Open Source LLM Framework",
        url="https://github.com/example/llm-framework",
        snippet="Community-driven LLM framework reaches 10k stars",
        source="github",
    ),
]

MOCK_RANKING_RESPONSE = {
    "research_pick": {
        "title": "GPT-5 Released with 10x Speed",
        "url": "https://openai.com/blog/gpt-5",
        "snippet": "OpenAI releases GPT-5 with massive performance improvements",
        "source": "tavily",
        "assigned_type": "research",
        "relevance_score": 0.95,
        "ranking_reason": "Major model release with significant benchmarks",
    },
    "business_main_pick": {
        "title": "Anthropic Raises $5B Series D",
        "url": "https://anthropic.com/news/series-d",
        "snippet": "Anthropic secures major funding round",
        "source": "tavily",
        "assigned_type": "business_main",
        "relevance_score": 0.88,
        "ranking_reason": "Largest AI safety funding round",
    },
    "related_picks": {
        "big_tech": None,
        "industry_biz": None,
        "new_tools": {
            "title": "New Open Source LLM Framework",
            "url": "https://github.com/example/llm-framework",
            "snippet": "Community-driven LLM framework reaches 10k stars",
            "source": "github",
            "assigned_type": "new_tools",
            "relevance_score": 0.72,
            "ranking_reason": "Popular new developer tool",
        },
    },
}

MOCK_RESEARCH_RESPONSE = {
    "has_news": True,
    "title": "GPT-5: 10배 빠른 추론 속도의 비밀",
    "slug": "2026-03-07-research-daily",
    "content_original": "OpenAI가 GPT-5를 공개했습니다...",
    "guide_items": {
        "one_liner": "GPT-5는 이전 모델 대비 10배 빠른 추론 속도를 달성했습니다",
        "action_item": "OpenAI API에서 gpt-5 모델을 테스트해보세요",
        "critical_gotcha": "추론 속도 개선은 배치 처리 기준이며, 단일 요청 지연시간은 미확인",
        "rotating_item": "GPT-4o 대비 API 호출 비용은 약 2배 증가할 것으로 예상됩니다",
        "quiz_poll": {
            "question": "GPT-5의 추론 속도 개선 배수는?",
            "options": ["5배", "10배", "20배", "50배"],
            "answer": "10배",
            "explanation": "공식 벤치마크 기준 GPT-4o 대비 10배입니다",
        },
    },
    "source_urls": ["https://openai.com/blog/gpt-5"],
    "news_temperature": 5,
    "tags": ["gpt-5", "openai", "llm"],
}

MOCK_RESEARCH_NO_NEWS_RESPONSE = {
    "has_news": False,
    "title": "AI 뉴스 없음 — 최근 동향 보충",
    "slug": "2026-03-07-research-daily",
    "no_news_notice": "지난 24시간(2026-03-06~07) 동안 공개된 실질적인 AI 기술 업데이트는 확인되지 않았습니다.",
    "recent_fallback": "최근 주목할 만한 동향: LLM 분야에서는...",
    "source_urls": [],
    "news_temperature": 1,
    "tags": ["no-news"],
}

MOCK_BUSINESS_RESPONSE = {
    "title": "Anthropic $5B 투자 유치 — AI 안전성 투자의 의미",
    "slug": "2026-03-07-business-daily",
    "content_beginner": "쉽게 말해, AI를 만드는 회사가 큰 돈을 받았어요...",
    "content_learner": "Anthropic의 시리즈 D 라운드는 AI 안전성 연구에...",
    "content_expert": "Anthropic의 $5B 시리즈 D는 AI safety 분야 최대 규모...",
    "guide_items": {
        "one_liner": "AI 안전 연구 회사가 역대 최대 투자를 받았습니다",
        "action_item": "Anthropic API 무료 크레딧으로 Claude를 테스트해보세요",
        "critical_gotcha": "투자 규모가 크다고 기술 우위가 보장되지는 않습니다",
        "rotating_item": "OpenAI vs Anthropic 경쟁 구도에서 투자금 차이는...",
        "quiz_poll": {
            "question": "Anthropic의 시리즈 D 투자 규모는?",
            "options": ["$1B", "$3B", "$5B", "$10B"],
            "answer": "$5B",
            "explanation": "AI safety 스타트업 역대 최대 규모입니다",
        },
    },
    "related_news": {
        "big_tech": None,
        "industry_biz": None,
        "new_tools": {
            "title": "New Open Source LLM Framework",
            "url": "https://github.com/example/llm-framework",
            "summary": "커뮤니티 주도 LLM 프레임워크가 10k 스타를 달성했습니다",
        },
    },
    "source_urls": ["https://anthropic.com/news/series-d"],
    "news_temperature": 4,
    "tags": ["anthropic", "investment", "ai-safety"],
}

MOCK_BUSINESS_FACT_PACK_RESPONSE = {
    "fact_pack": [
        {
            "id": "claim-1",
            "claim": "Anthropic closed a major new funding round. [[1]]",
            "why_it_matters": "More capital changes buyer confidence and compute planning.",
            "source_ids": ["src-1"],
            "confidence": "high",
        },
        {
            "id": "claim-2",
            "claim": "The raise strengthens Anthropic's enterprise positioning. [[1]][[2]]",
            "why_it_matters": "Enterprise buyers care about vendor durability as much as model quality.",
            "source_ids": ["src-1", "src-2"],
            "confidence": "medium",
        },
    ],
    "source_cards": [
        {
            "id": "src-1",
            "title": "Anthropic funding announcement",
            "publisher": "Anthropic",
            "url": "https://anthropic.com/news/series-d",
            "published_at": "2026-03-07T00:00:00Z",
            "evidence_snippet": "Official announcement confirming the funding round and expansion plans.",
            "claim_ids": ["claim-1", "claim-2"],
        },
        {
            "id": "src-2",
            "title": "Enterprise AI market analysis",
            "publisher": "FT",
            "url": "https://ft.com/ai-enterprise-analysis",
            "published_at": "2026-03-07T00:00:00Z",
            "evidence_snippet": "Buyers are increasingly sensitive to platform durability and compute access.",
            "claim_ids": ["claim-2"],
        },
    ],
}

def _make_long_markdown(section_titles: list[str], section_length: int, filler: str) -> str:
    sections = []
    for title in section_titles:
        body_length = max(section_length - len(title) - 1, 0)
        body = (filler * ((body_length // len(filler)) + 2))[:body_length]
        sections.append(f"{title}\n{body}")
    return "\n\n".join(sections)


MOCK_BUSINESS_ANALYSIS_RESPONSE = {
    "title": "Anthropic's new funding reshapes enterprise AI positioning",
    "slug": "2026-03-07-business-daily",
    "content_analysis": _make_long_markdown(
        ["## Core Analysis", "## Why This Matters", "## Strategic Outlook"],
        1300,
        "Shared market analysis with buyer trust, pricing leverage, and sourcing detail. [[1]] ",
    ),
    "excerpt": "Anthropic's funding round changes how enterprise buyers read vendor durability and platform risk.",
    "focus_items": [
        "Anthropic added more capital to support model, compute, and enterprise expansion.",
        "Balance-sheet strength changes how large buyers evaluate AI platform risk.",
        "Pricing, hiring, and capacity announcements are the next signals to watch.",
    ],
    "guide_items": {
        "one_liner": "Anthropic raised more money to grow its enterprise AI business.",
        "action_item": "Review whether your roadmap depends too heavily on a single model vendor.",
        "critical_gotcha": "Funding size does not guarantee better margins or product execution.",
        "rotating_item": "Financial depth often matters to enterprise buyers before benchmark wins do.",
        "quiz_poll": {
            "question": "What does a large AI funding round most directly increase first?",
            "options": ["Compute access", "Wall color", "Mascot quality", "Office snacks"],
            "answer": "A",
            "explanation": "Big rounds usually increase compute access, hiring capacity, and enterprise execution.",
        },
    },
    "related_news": {
        "big_tech": None,
        "industry_biz": None,
        "new_tools": {
            "title": "New Open Source LLM Framework",
            "url": "https://github.com/example/llm-framework",
            "summary": "Community-driven LLM framework reached 10k stars and drew strong developer adoption.",
        },
    },
    "source_urls": ["https://anthropic.com/news/series-d"],
    "news_temperature": 4,
    "tags": ["anthropic", "investment", "ai-safety"],
}

MOCK_BUSINESS_PERSONA_RESPONSES = {
    "beginner": {
        "content_beginner": _make_long_markdown(
            ["## The Story", "## Why Should I Care?", "## The Bottom Line"],
            1500,
            "Plain-language business explanation with examples about products, jobs, and customer trust. ",
        )
    },
    "learner": {
        "content_learner": _make_long_markdown(
            ["## What Happened", "## How It Works", "## What This Means for Your Work", "## Go Deeper"],
            1200,
            "Practical technical-business analysis with architecture, pricing, and team workflow implications. ",
        )
    },
    "expert": {
        "content_expert": _make_long_markdown(
            ["## Executive Summary", "## Technical Deep Dive", "## Market & Competitive Analysis", "## Strategic Implications"],
            1200,
            "Executive-level competitive analysis with market structure, capital strategy, and deployment risk detail. ",
        )
    },
}


MOCK_RESEARCH_RESPONSE = {
    "has_news": True,
    "title": "GPT-5: lower latency and stronger multimodal throughput",
    "slug": "2026-03-07-research-daily",
    "content_original": _make_long_markdown(
        [
            "## 1. What Happened",
            "## 2. By the Numbers",
            "## 3. So What",
            "## 4. Deep Dive",
        ],
        1600,
        "Source-backed technical explanation with benchmark detail and deployment context. ",
    ),
    "excerpt": "GPT-5 improved latency enough to change how teams evaluate production UX and cost tradeoffs.",
    "focus_items": [
        "GPT-5 reduced latency across multimodal inference paths.",
        "Lower latency changes product design and budget assumptions for interactive AI.",
        "The next release notes should confirm pricing and throughput tradeoffs.",
    ],
    "guide_items": {
        "one_liner": "GPT-5 is a faster multimodal model update for production inference.",
        "action_item": "Benchmark your current prompts against GPT-5 latency and stability.",
        "critical_gotcha": "Lower latency does not guarantee lower cost or better long-context performance.",
        "rotating_item": "The market signal matters only if the speed gains persist under real production load.",
        "quiz_poll": {
            "question": "What should teams validate first after a latency-focused release?",
            "options": ["Branding", "Reliability", "Office layout", "Mascot"],
            "answer": "B",
            "explanation": "Teams need reliable outputs before they can safely optimize around faster responses.",
        },
    },
    "source_urls": ["https://openai.com/blog/gpt-5"],
    "news_temperature": 5,
    "tags": ["gpt-5", "openai", "llm"],
}


MOCK_BUSINESS_RESPONSE = {
    "title": "Anthropic's new funding reshapes enterprise AI positioning",
    "slug": "2026-03-07-business-daily",
    "content_beginner": _make_long_markdown(
        ["## The Story", "## Why Should I Care?", "## The Bottom Line"],
        1500,
        "Plain-language business explanation with examples about products, jobs, and customer trust. ",
    ),
    "content_learner": _make_long_markdown(
        ["## What Happened", "## How It Works", "## What This Means for Your Work", "## Go Deeper"],
        1200,
        "Practical technical-business analysis with architecture, pricing, and team workflow implications. ",
    ),
    "content_expert": _make_long_markdown(
        ["## Executive Summary", "## Technical Deep Dive", "## Market & Competitive Analysis", "## Strategic Implications"],
        1200,
        "Executive-level competitive analysis with market structure, capital strategy, and deployment risk detail. ",
    ),
    "excerpt": "Anthropic's funding round changes how enterprise buyers read vendor durability and platform risk.",
    "focus_items": [
        "Anthropic added more capital to support model, compute, and enterprise expansion.",
        "Balance-sheet strength changes how large buyers evaluate AI platform risk.",
        "Pricing, hiring, and capacity announcements are the next signals to watch.",
    ],
    "guide_items": {
        "one_liner": "Anthropic raised more money to grow its enterprise AI business.",
        "action_item": "Review whether your roadmap depends too heavily on a single model vendor.",
        "critical_gotcha": "Funding size does not guarantee better margins or product execution.",
        "rotating_item": "Financial depth often matters to enterprise buyers before benchmark wins do.",
        "quiz_poll": {
            "question": "What does a large AI funding round most directly increase first?",
            "options": ["Compute access", "Wall color", "Mascot quality", "Office snacks"],
            "answer": "A",
            "explanation": "Big rounds usually increase compute access, hiring capacity, and enterprise execution.",
        },
    },
    "related_news": {
        "big_tech": None,
        "industry_biz": None,
        "new_tools": {
            "title": "New Open Source LLM Framework",
            "url": "https://github.com/example/llm-framework",
            "summary": "Community-driven LLM framework reached 10k stars and drew strong developer adoption.",
        },
    },
    "source_urls": ["https://anthropic.com/news/series-d"],
    "news_temperature": 4,
    "tags": ["anthropic", "investment", "ai-safety"],
}


# ---------------------------------------------------------------------------
# Helper: create a mock OpenAI response
# ---------------------------------------------------------------------------

def _mock_openai_response(
    data: dict,
    *,
    prompt_tokens: int = 800,
    completion_tokens: int = 200,
) -> MagicMock:
    """Create a mock that mimics openai chat completion response."""
    choice = MagicMock()
    choice.message.content = json.dumps(data)
    response = MagicMock()
    response.choices = [choice]
    response.usage = MagicMock(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )
    return response


# ---------------------------------------------------------------------------
# Ranking Agent Tests
# ---------------------------------------------------------------------------

class TestRankingAgent:
    @pytest.mark.asyncio
    async def test_rank_candidates_returns_valid_result(self):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_openai_response(MOCK_RANKING_RESPONSE)
        )

        with patch("services.agents.ranking.get_openai_client", return_value=mock_client):
            from services.agents.ranking import rank_candidates
            result = await rank_candidates(SAMPLE_CANDIDATES)

        assert isinstance(result, NewsRankingResult)
        assert result.research_pick.assigned_type == "research"
        assert result.business_main_pick.assigned_type == "business_main"
        assert result.related_picks.new_tools is not None
        assert result.related_picks.big_tech is None

    @pytest.mark.asyncio
    async def test_rank_candidates_calls_light_model(self):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_openai_response(MOCK_RANKING_RESPONSE)
        )

        with patch("services.agents.ranking.get_openai_client", return_value=mock_client):
            from services.agents.ranking import rank_candidates
            await rank_candidates(SAMPLE_CANDIDATES)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_rank_candidates_records_usage_metrics(self):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_openai_response(
                MOCK_RANKING_RESPONSE,
                prompt_tokens=1200,
                completion_tokens=300,
            )
        )
        usage = {}

        with patch("services.agents.ranking.get_openai_client", return_value=mock_client):
            from services.agents.ranking import rank_candidates
            await rank_candidates(SAMPLE_CANDIDATES, usage_recorder=usage)

        assert usage["tokens_used"] == 1500
        assert usage["input_tokens"] == 1200
        assert usage["output_tokens"] == 300
        assert usage["cost_usd"] is not None

    @pytest.mark.asyncio
    async def test_rank_candidates_uses_json_format(self):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_openai_response(MOCK_RANKING_RESPONSE)
        )

        with patch("services.agents.ranking.get_openai_client", return_value=mock_client):
            from services.agents.ranking import rank_candidates
            await rank_candidates(SAMPLE_CANDIDATES)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["response_format"] == {"type": "json_object"}


# ---------------------------------------------------------------------------
# Research Agent Tests
# ---------------------------------------------------------------------------

class TestResearchAgent:
    @pytest.mark.asyncio
    async def test_generate_research_post_with_news(self):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_openai_response(MOCK_RESEARCH_RESPONSE)
        )

        candidate = RankedCandidate(**MOCK_RANKING_RESPONSE["research_pick"])

        with patch("services.agents.research.get_openai_client", return_value=mock_client):
            from services.agents.research import generate_research_post
            result = await generate_research_post(
                candidate=candidate,
                context="Tavily collected context...",
                batch_id="2026-03-07",
            )

        assert isinstance(result, ResearchPost)
        assert result.has_news is True
        assert result.content_original is not None
        assert result.guide_items is not None
        assert result.news_temperature == 5

    @pytest.mark.asyncio
    async def test_generate_research_post_records_usage_metrics(self):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_openai_response(
                MOCK_RESEARCH_RESPONSE,
                prompt_tokens=2400,
                completion_tokens=600,
            )
        )

        candidate = RankedCandidate(**MOCK_RANKING_RESPONSE["research_pick"])
        usage = {}

        with patch("services.agents.research.get_openai_client", return_value=mock_client):
            from services.agents.research import generate_research_post

            await generate_research_post(
                candidate=candidate,
                context="Tavily collected context...",
                batch_id="2026-03-07",
                usage_recorder=usage,
            )

        assert usage["tokens_used"] >= 3000
        assert usage["cost_usd"] is not None

    @pytest.mark.asyncio
    async def test_generate_research_post_no_news(self):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_openai_response(MOCK_RESEARCH_NO_NEWS_RESPONSE)
        )

        with patch("services.agents.research.get_openai_client", return_value=mock_client):
            from services.agents.research import generate_research_post
            result = await generate_research_post(
                candidate=None,
                context="",
                batch_id="2026-03-07",
            )

        assert isinstance(result, ResearchPost)
        assert result.has_news is False
        assert result.no_news_notice is not None
        assert result.recent_fallback is not None
        assert result.content_original is None

    @pytest.mark.asyncio
    async def test_research_agent_calls_main_model(self):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_openai_response(MOCK_RESEARCH_RESPONSE)
        )

        candidate = RankedCandidate(**MOCK_RANKING_RESPONSE["research_pick"])

        with patch("services.agents.research.get_openai_client", return_value=mock_client):
            from services.agents.research import generate_research_post
            await generate_research_post(candidate, "ctx", "2026-03-07")

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o"


# ---------------------------------------------------------------------------
# Business Agent Tests
# ---------------------------------------------------------------------------

class TestBusinessAgent:
    @pytest.mark.asyncio
    async def test_generate_business_post(self):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                _mock_openai_response(MOCK_BUSINESS_FACT_PACK_RESPONSE),
                _mock_openai_response(MOCK_BUSINESS_ANALYSIS_RESPONSE),
                _mock_openai_response(MOCK_BUSINESS_PERSONA_RESPONSES["beginner"]),
                _mock_openai_response(MOCK_BUSINESS_PERSONA_RESPONSES["learner"]),
                _mock_openai_response(MOCK_BUSINESS_PERSONA_RESPONSES["expert"]),
            ]
        )

        candidate = RankedCandidate(**MOCK_RANKING_RESPONSE["business_main_pick"])
        related = RelatedPicks(**MOCK_RANKING_RESPONSE["related_picks"])

        with patch("services.agents.business.get_openai_client", return_value=mock_client):
            from services.agents.business import generate_business_post
            result = await generate_business_post(
                candidate=candidate,
                related=related,
                context="Tavily collected context...",
                batch_id="2026-03-07",
            )

        assert isinstance(result, BusinessPost)
        assert result.content_beginner is not None
        assert result.content_learner is not None
        assert result.content_expert is not None
        assert result.content_analysis is not None
        assert result.fact_pack is not None
        assert result.source_cards is not None
        assert result.guide_items is not None
        assert result.related_news is not None
        assert result.news_temperature == 4

    @pytest.mark.asyncio
    async def test_generate_business_post_stage_logger_receives_usage_metrics(self):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                _mock_openai_response(MOCK_BUSINESS_FACT_PACK_RESPONSE, prompt_tokens=1000, completion_tokens=200),
                _mock_openai_response(MOCK_BUSINESS_ANALYSIS_RESPONSE, prompt_tokens=1200, completion_tokens=400),
                _mock_openai_response(MOCK_BUSINESS_PERSONA_RESPONSES["beginner"], prompt_tokens=900, completion_tokens=500),
                _mock_openai_response(MOCK_BUSINESS_PERSONA_RESPONSES["learner"], prompt_tokens=900, completion_tokens=500),
                _mock_openai_response(MOCK_BUSINESS_PERSONA_RESPONSES["expert"], prompt_tokens=900, completion_tokens=500),
            ]
        )

        candidate = RankedCandidate(**MOCK_RANKING_RESPONSE["business_main_pick"])
        related = RelatedPicks(**MOCK_RANKING_RESPONSE["related_picks"])
        emitted = []

        def stage_logger(stage_name, status, attempt, debug_meta, output_summary, model_used, tokens_used, cost_usd):
            emitted.append(
                {
                    "stage_name": stage_name,
                    "status": status,
                    "attempt": attempt,
                    "model_used": model_used,
                    "tokens_used": tokens_used,
                    "cost_usd": cost_usd,
                }
            )

        with patch("services.agents.business.get_openai_client", return_value=mock_client):
            from services.agents.business import generate_business_post

            await generate_business_post(
                candidate=candidate,
                related=related,
                context="Tavily collected context...",
                batch_id="2026-03-07",
                stage_logger=stage_logger,
            )

        assert any(entry["stage_name"] == "business.fact_pack.en" for entry in emitted)
        assert all(entry["model_used"] == "gpt-4o" for entry in emitted)
        assert all(isinstance(entry["tokens_used"], int) and entry["tokens_used"] > 0 for entry in emitted)
        assert all(entry["cost_usd"] is not None for entry in emitted)

    @pytest.mark.asyncio
    async def test_business_agent_calls_main_model(self):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                _mock_openai_response(MOCK_BUSINESS_FACT_PACK_RESPONSE),
                _mock_openai_response(MOCK_BUSINESS_ANALYSIS_RESPONSE),
                _mock_openai_response(MOCK_BUSINESS_PERSONA_RESPONSES["beginner"]),
                _mock_openai_response(MOCK_BUSINESS_PERSONA_RESPONSES["learner"]),
                _mock_openai_response(MOCK_BUSINESS_PERSONA_RESPONSES["expert"]),
            ]
        )

        candidate = RankedCandidate(**MOCK_RANKING_RESPONSE["business_main_pick"])
        related = RelatedPicks(**MOCK_RANKING_RESPONSE["related_picks"])

        with patch("services.agents.business.get_openai_client", return_value=mock_client):
            from services.agents.business import generate_business_post
            await generate_business_post(candidate, related, "ctx", "2026-03-07")

        assert mock_client.chat.completions.create.await_count == 5
        for call in mock_client.chat.completions.create.await_args_list:
            assert call.kwargs["model"] == "gpt-4o"

    @pytest.mark.asyncio
    async def test_business_post_three_personas_differ(self):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                _mock_openai_response(MOCK_BUSINESS_FACT_PACK_RESPONSE),
                _mock_openai_response(MOCK_BUSINESS_ANALYSIS_RESPONSE),
                _mock_openai_response(MOCK_BUSINESS_PERSONA_RESPONSES["beginner"]),
                _mock_openai_response(MOCK_BUSINESS_PERSONA_RESPONSES["learner"]),
                _mock_openai_response(MOCK_BUSINESS_PERSONA_RESPONSES["expert"]),
            ]
        )

        candidate = RankedCandidate(**MOCK_RANKING_RESPONSE["business_main_pick"])
        related = RelatedPicks(**MOCK_RANKING_RESPONSE["related_picks"])

        with patch("services.agents.business.get_openai_client", return_value=mock_client):
            from services.agents.business import generate_business_post
            result = await generate_business_post(candidate, related, "ctx", "2026-03-07")

        # 3 personas should have different content
        assert result.content_beginner != result.content_learner
        assert result.content_learner != result.content_expert


# ---------------------------------------------------------------------------
# Network blocking verification
# ---------------------------------------------------------------------------

class TestNetworkBlocking:
    @pytest.mark.asyncio
    async def test_real_openai_call_is_blocked(self):
        """Verify that a real OpenAI call raises due to network blocking."""
        from services.agents.client import get_openai_client
        client = get_openai_client()

        with pytest.raises(Exception):
            await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "test"}],
            )

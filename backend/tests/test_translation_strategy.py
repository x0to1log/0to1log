"""Tests for whole-post translation (v4: single gpt-4o call per post)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.business import (
    KO_MIN_ANALYSIS_CHARS as BUSINESS_KO_MIN_ANALYSIS_CHARS,
    KO_MIN_CONTENT_CHARS as BUSINESS_KO_MIN_CONTENT_CHARS,
    BusinessPost,
)
from models.research import KO_MIN_CONTENT_CHARS as RESEARCH_KO_MIN_CONTENT_CHARS, ResearchPost


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    import httpx

    def _blocked(*args, **kwargs):
        raise RuntimeError("Real network call blocked in tests!")

    monkeypatch.setattr(httpx.AsyncClient, "send", _blocked)
    monkeypatch.setattr(httpx.Client, "send", _blocked)


def _mock_openai_response(data: dict, prompt_tokens: int = 500, completion_tokens: int = 300) -> MagicMock:
    choice = MagicMock()
    choice.message.content = json.dumps(data, ensure_ascii=False)
    response = MagicMock()
    response.choices = [choice]
    response.usage = MagicMock(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )
    return response


def _filler(length: int, phrase: str = "Korean-style sentence with detail. ") -> str:
    return (phrase * ((length // len(phrase)) + 2))[:length]


# ---------------------------------------------------------------------------
# Research fixtures
# ---------------------------------------------------------------------------

def _make_research_en_post() -> dict:
    return {
        "has_news": True,
        "title": "GPT-5 reduces latency for multimodal workloads",
        "slug": "2026-03-12-research-daily",
        "content_original": "## 1. What Happened\n" + _filler(1600) + "\n\n## 2. By the Numbers\n" + _filler(1600) + "\n\n## 3. Why It Matters\n" + _filler(1600) + "\n\n## 4. Deep Dive\n" + _filler(1600),
        "excerpt": "OpenAI reduced latency while keeping enough context for practical production evaluation.",
        "focus_items": [
            "GPT-5 improved latency on multimodal inference paths.",
            "Lower latency changes product and cost planning for interactive AI.",
            "Watch for pricing and throughput disclosures in the next release notes.",
        ],
        "guide_items": {
            "one_liner": "GPT-5 is a faster multimodal model release for production inference.",
            "action_item": "Benchmark your current prompts against the new latency profile.",
            "critical_gotcha": "Latency gains can still come with cost and throughput tradeoffs.",
            "rotating_item": "The biggest question is whether speed gains hold on long-context workloads.",
            "quiz_poll": {
                "question": "Which metric matters first after a latency-focused release?",
                "options": ["Throughput", "Reliability", "Logo refresh", "Blog length"],
                "answer": "B",
                "explanation": "Teams need to confirm outputs remain reliable before optimizing around latency.",
            },
        },
        "source_urls": ["https://openai.com/blog/example"],
        "news_temperature": 4,
        "tags": ["gpt-5", "latency", "multimodal"],
    }


def _make_research_ko_full() -> dict:
    """Full Korean translation payload for a research post."""
    ko_content = "## 1. 무슨 일이 있었나\n" + _filler(1600, "한국어 번역된 기술 분석 문장입니다. ") + "\n\n## 2. 숫자로 보기\n" + _filler(1600, "한국어 번역된 기술 분석 문장입니다. ") + "\n\n## 3. 왜 중요한가\n" + _filler(1600, "한국어 번역된 기술 분석 문장입니다. ") + "\n\n## 4. 심층 분석\n" + _filler(1600, "한국어 번역된 기술 분석 문장입니다. ")
    return {
        "title": "GPT-5 한국어 제목",
        "excerpt": "한국어 번역된 요약 텍스트입니다.",
        "tags": ["gpt-5", "latency", "multimodal"],
        "focus_items": [
            "GPT-5 멀티모달 추론 경로에서 지연 시간이 개선되었습니다.",
            "지연 시간 감소는 인터랙티브 AI의 제품 및 비용 계획을 변경합니다.",
            "다음 릴리스 노트에서 가격 및 처리량 공개를 주시하세요.",
        ],
        "guide_items": {
            "one_liner": "GPT-5는 프로덕션 추론을 위한 더 빠른 멀티모달 모델 릴리스입니다.",
            "action_item": "현재 프롬프트를 새로운 지연 시간 프로필과 비교 벤치마크하세요.",
            "critical_gotcha": "지연 시간 개선은 여전히 비용 및 처리량 트레이드오프를 동반할 수 있습니다.",
            "rotating_item": "가장 큰 질문은 속도 개선이 긴 컨텍스트 작업에서도 유지되는지입니다.",
            "quiz_poll": {
                "question": "지연 시간 중심 릴리스 후 가장 먼저 중요한 지표는?",
                "options": ["처리량", "안정성", "로고 새로고침", "블로그 길이"],
                "answer": "B",
                "explanation": "팀은 지연 시간을 최적화하기 전에 출력이 안정적인지 확인해야 합니다.",
            },
        },
        "content_original": ko_content,
    }


def _make_research_ko_short() -> dict:
    """Korean translation with content_original below minimum length."""
    ko = _make_research_ko_full()
    ko["content_original"] = "## 1. 짧은 섹션\n" + _filler(500, "짧은 한국어 문장. ")
    return ko


# ---------------------------------------------------------------------------
# Business fixtures
# ---------------------------------------------------------------------------

def _make_business_en_post() -> dict:
    filler = "Business explanation with operational implications, competitive analysis, and buyer impact. "
    return {
        "title": "Anthropic expands enterprise AI financing",
        "slug": "2026-03-12-business-daily",
        "content_analysis": "## Core Analysis\n" + _filler(3000, filler),
        "content_beginner": "## The Story\n" + _filler(5200, filler),
        "content_learner": "## What Happened\n" + _filler(5200, filler),
        "content_expert": "## Executive Summary\n" + _filler(5200, filler),
        "excerpt": "Anthropic's funding round changes how enterprise buyers read platform risk.",
        "focus_items": [
            "Anthropic added more capital to support product and compute expansion.",
            "Enterprise buyers read financial depth as a delivery-risk signal.",
            "Pricing and hiring moves are the next practical signals to watch.",
        ],
        "guide_items": {
            "one_liner": "Anthropic raised more capital to expand enterprise AI operations.",
            "action_item": "Review single-vendor assumptions in your AI roadmap this quarter.",
            "critical_gotcha": "Funding does not guarantee better cost structure or product execution.",
            "rotating_item": "Balance-sheet strength affects buyer trust long before benchmark results change.",
            "quiz_poll": {
                "question": "What does major AI financing most directly change first?",
                "options": ["Compute access", "Mascot quality", "Wallpaper", "Snacks"],
                "answer": "A",
                "explanation": "Large rounds usually increase compute access and enterprise execution capacity.",
            },
        },
        "related_news": {
            "big_tech": None,
            "industry_biz": {
                "title": "OpenAI expands enterprise bundles",
                "url": "https://openai.com/blog/bundles",
                "summary": "OpenAI introduced broader contract options for large teams evaluating AI at scale.",
            },
            "new_tools": None,
        },
        "fact_pack": {
            "key_facts": ["Anthropic expanded enterprise financing."],
            "numbers": ["New funding amount not disclosed publicly."],
            "entities": ["Anthropic", "Enterprise AI"],
            "timeline": ["2026-Q1 — Funding round announced."],
        },
        "source_cards": [
            {
                "id": "src-1",
                "title": "Anthropic financing announcement",
                "publisher": "Anthropic",
                "url": "https://anthropic.com/news/example",
                "published_at": "2026-03-12T00:00:00Z",
                "evidence_snippet": "Anthropic said the financing will support enterprise and compute expansion.",
                "claim_ids": ["claim-1"],
            }
        ],
        "source_urls": ["https://anthropic.com/news/example"],
        "news_temperature": 4,
        "tags": ["anthropic", "enterprise", "funding"],
    }


def _make_business_ko_full() -> dict:
    """Full Korean translation payload for a business post."""
    ko_filler = "한국어 비즈니스 분석 문장으로 운영적 함의와 경쟁 분석 및 구매자 영향을 포함합니다. "
    return {
        "title": "Anthropic 한국어 제목",
        "excerpt": "한국어 비즈니스 요약 텍스트입니다.",
        "tags": ["anthropic", "enterprise", "funding"],
        "focus_items": [
            "Anthropic은 제품 및 컴퓨트 확장을 위해 더 많은 자본을 추가했습니다.",
            "엔터프라이즈 구매자들은 재무 건전성을 전달 위험 신호로 읽습니다.",
            "가격 및 채용 움직임이 다음 실질적인 신호입니다.",
        ],
        "guide_items": {
            "one_liner": "Anthropic은 엔터프라이즈 AI 운영 확장을 위해 추가 자본을 조달했습니다.",
            "action_item": "이번 분기 AI 로드맵에서 단일 벤더 가정을 검토하세요.",
            "critical_gotcha": "자금 조달이 더 나은 비용 구조나 제품 실행을 보장하지는 않습니다.",
            "rotating_item": "재무 건전성은 벤치마크 결과가 변하기 훨씬 전에 구매자 신뢰에 영향을 미칩니다.",
            "quiz_poll": {
                "question": "주요 AI 자금 조달이 가장 먼저 직접적으로 변화시키는 것은?",
                "options": ["컴퓨트 접근성", "마스코트 품질", "배경화면", "간식"],
                "answer": "A",
                "explanation": "대규모 투자는 일반적으로 컴퓨트 접근성과 엔터프라이즈 실행 역량을 증가시킵니다.",
            },
        },
        "related_news": {
            "big_tech": None,
            "industry_biz": {
                "title": "OpenAI 엔터프라이즈 번들 확장",
                "url": "https://openai.com/blog/bundles",
                "summary": "OpenAI는 대규모 팀을 위한 더 넓은 계약 옵션을 도입했습니다.",
            },
            "new_tools": None,
        },
        "fact_pack": {
            "key_facts": ["Anthropic이 엔터프라이즈 자금을 확대했습니다."],
            "numbers": ["새로운 자금 규모는 공개되지 않았습니다."],
            "entities": ["Anthropic", "엔터프라이즈 AI"],
            "timeline": ["2026년 1분기 — 자금 조달 라운드 발표."],
        },
        "content_analysis": "## 핵심 분석\n" + _filler(2200, ko_filler),
        "content_beginner": "## 이야기\n" + _filler(4200, ko_filler),
        "content_learner": "## 무슨 일이 있었나\n" + _filler(4200, ko_filler),
        "content_expert": "## 경영진 요약\n" + _filler(4200, ko_filler),
    }


def _make_business_ko_short_fields() -> dict:
    """Korean translation with some persona fields below minimum length."""
    ko = _make_business_ko_full()
    ko["content_learner"] = "## 짧은 학습자 섹션\n" + _filler(500, "짧은 한국어. ")
    return ko


# ---------------------------------------------------------------------------
# Research translation tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_translate_research_post_whole_post_success():
    """Single gpt-4o call translates the full research post and returns (dict, usage)."""
    en_data = _make_research_en_post()
    ko_full = _make_research_ko_full()

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response(ko_full)
    )

    with patch("services.agents.translate.get_openai_client", return_value=mock_client):
        from services.agents.translate import translate_post

        ko_data, usage = await translate_post(en_data, "research")

    validated = ResearchPost.model_validate(ko_data)
    assert validated.content_original is not None
    assert len(validated.content_original) >= RESEARCH_KO_MIN_CONTENT_CHARS
    assert validated.title == ko_full["title"]
    assert mock_client.chat.completions.create.await_count == 1

    # Usage metrics returned as second tuple element
    assert usage["tokens_used"] > 0


@pytest.mark.asyncio
async def test_translate_research_post_retries_on_short_content():
    """When content_original is too short, the translator retries with an expanded prompt."""
    en_data = _make_research_en_post()
    ko_short = _make_research_ko_short()
    ko_full = _make_research_ko_full()

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(ko_short),
            _mock_openai_response(ko_full),
        ]
    )

    with patch("services.agents.translate.get_openai_client", return_value=mock_client):
        from services.agents.translate import translate_post

        ko_data, usage = await translate_post(en_data, "research")

    validated = ResearchPost.model_validate(ko_data)
    assert validated.content_original is not None
    assert len(validated.content_original) >= RESEARCH_KO_MIN_CONTENT_CHARS
    assert mock_client.chat.completions.create.await_count == 2

    # Second call prompt should mention the short content
    retry_prompt = mock_client.chat.completions.create.await_args_list[1].kwargs["messages"][1]["content"]
    assert "content_original" in retry_prompt


@pytest.mark.asyncio
async def test_translate_research_post_returns_usage_metrics():
    """Usage metrics are accumulated across retries and returned."""
    en_data = _make_research_en_post()
    ko_full = _make_research_ko_full()

    resp = _mock_openai_response(ko_full, prompt_tokens=800, completion_tokens=600)
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=resp)

    with patch("services.agents.translate.get_openai_client", return_value=mock_client):
        from services.agents.translate import translate_post

        _, usage = await translate_post(en_data, "research")

    assert usage["tokens_used"] > 0
    assert usage["input_tokens"] > 0
    assert usage["output_tokens"] > 0
    assert usage["cost_usd"] is not None


@pytest.mark.asyncio
async def test_translate_research_no_news_skips_content_validation():
    """No-news research posts skip content_original length validation."""
    en_data = {
        "has_news": False,
        "title": "No sufficiently distinct research update today",
        "slug": "2026-03-12-research-daily",
        "content_original": None,
        "no_news_notice": "No sufficiently distinct AI research updates were confirmed in the last 24 hours.",
        "recent_fallback": "Yesterday's themes still dominated the signal landscape.",
        "excerpt": "",
        "focus_items": [],
        "guide_items": None,
        "source_urls": [],
        "news_temperature": 1,
        "tags": ["no-news"],
    }
    ko_payload = {
        "title": "오늘은 충분히 다른 AI 연구 업데이트가 없었습니다",
        "no_news_notice": "오늘은 충분히 다른 AI 연구 업데이트가 확인되지 않았습니다.",
        "recent_fallback": "어제의 주요 흐름이 계속 이어졌습니다.",
        "focus_items": [],
        "guide_items": None,
        "tags": ["no-news"],
    }
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response(ko_payload)
    )

    with patch("services.agents.translate.get_openai_client", return_value=mock_client):
        from services.agents.translate import translate_post

        ko_data, usage = await translate_post(en_data, "research")

    validated = ResearchPost.model_validate(ko_data)
    assert validated.has_news is False
    assert validated.content_original is None
    assert mock_client.chat.completions.create.await_count == 1


# ---------------------------------------------------------------------------
# Business translation tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_translate_business_post_whole_post_success():
    """Single gpt-4o call translates the full business post."""
    en_data = _make_business_en_post()
    ko_full = _make_business_ko_full()

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response(ko_full)
    )

    with patch("services.agents.translate.get_openai_client", return_value=mock_client):
        from services.agents.translate import translate_post

        ko_data, usage = await translate_post(en_data, "business")

    validated = BusinessPost.model_validate(ko_data)
    assert len(validated.content_analysis) >= BUSINESS_KO_MIN_ANALYSIS_CHARS
    assert len(validated.content_beginner) >= BUSINESS_KO_MIN_CONTENT_CHARS
    assert len(validated.content_learner) >= BUSINESS_KO_MIN_CONTENT_CHARS
    assert len(validated.content_expert) >= BUSINESS_KO_MIN_CONTENT_CHARS
    assert mock_client.chat.completions.create.await_count == 1


@pytest.mark.asyncio
async def test_translate_business_post_retries_on_short_fields():
    """When persona or analysis fields are too short, the translator retries."""
    en_data = _make_business_en_post()
    ko_short = _make_business_ko_short_fields()
    ko_full = _make_business_ko_full()

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(ko_short),
            _mock_openai_response(ko_full),
        ]
    )

    with patch("services.agents.translate.get_openai_client", return_value=mock_client):
        from services.agents.translate import translate_post

        ko_data, usage = await translate_post(en_data, "business")

    validated = BusinessPost.model_validate(ko_data)
    assert len(validated.content_learner) >= BUSINESS_KO_MIN_CONTENT_CHARS
    assert mock_client.chat.completions.create.await_count == 2

    retry_prompt = mock_client.chat.completions.create.await_args_list[1].kwargs["messages"][1]["content"]
    assert "content_learner" in retry_prompt


@pytest.mark.asyncio
async def test_translate_business_post_fails_after_max_retries():
    """After MAX_RETRIES, raises ValueError if fields stay too short."""
    en_data = _make_business_en_post()
    ko_short = _make_business_ko_short_fields()

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response(ko_short)
    )

    with patch("services.agents.translate.get_openai_client", return_value=mock_client):
        from services.agents.translate import translate_post

        with pytest.raises(ValueError, match="TranslateBusiness failed"):
            await translate_post(en_data, "business")

    # 1 initial + 2 retries = 3 total calls
    assert mock_client.chat.completions.create.await_count == 3


def test_business_post_allows_shorter_korean_lengths():
    """BusinessPost Pydantic model accepts KO-length content (>= KO_MIN thresholds)."""
    ko_filler = "한국어 비즈니스 분석 문장. "
    analysis = "## Core Analysis\n" + _filler(BUSINESS_KO_MIN_ANALYSIS_CHARS + 73, ko_filler)
    beginner = "## Beginner View\n" + _filler(BUSINESS_KO_MIN_CONTENT_CHARS + 93, ko_filler)
    learner = "## Learner View\n" + _filler(BUSINESS_KO_MIN_CONTENT_CHARS + 183, ko_filler)
    expert = "## Expert View\n" + _filler(BUSINESS_KO_MIN_CONTENT_CHARS + 220, ko_filler)

    post = BusinessPost.model_validate(
        {
            "title": "Legora raises a larger financing round",
            "slug": "2026-03-12-business-daily",
            "content_analysis": analysis,
            "content_beginner": beginner,
            "content_learner": learner,
            "content_expert": expert,
            "source_urls": ["https://example.com/legora"],
            "news_temperature": 3,
            "tags": ["legora"],
        }
    )

    assert len(post.content_analysis) >= BUSINESS_KO_MIN_ANALYSIS_CHARS
    assert len(post.content_beginner) >= BUSINESS_KO_MIN_CONTENT_CHARS
    assert len(post.content_learner) >= BUSINESS_KO_MIN_CONTENT_CHARS
    assert len(post.content_expert) >= BUSINESS_KO_MIN_CONTENT_CHARS

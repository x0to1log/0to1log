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


def _mock_openai_response(data: dict) -> MagicMock:
    choice = MagicMock()
    choice.message.content = json.dumps(data, ensure_ascii=False)
    response = MagicMock()
    response.choices = [choice]
    return response


def _make_markdown_sections(section_titles: list[str], section_length: int, filler: str) -> str:
    sections = []
    for title in section_titles:
        body_length = max(section_length - len(title) - 1, 0)
        body = (filler * ((body_length // len(filler)) + 2))[:body_length]
        sections.append(f"{title}\n{body}")
    return "\n\n".join(sections)


def _make_research_en_post() -> dict:
    return {
        "has_news": True,
        "title": "GPT-5 reduces latency for multimodal workloads",
        "slug": "2026-03-12-research-daily",
        "content_original": _make_markdown_sections(
            [
                "## 1. What Happened",
                "## 2. By the Numbers",
                "## 3. So What",
                "## 4. Deep Dive",
            ],
            1600,
            "Technical source-backed explanation with implementation detail and benchmark context. ",
        ),
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


def _make_research_metadata_ko() -> dict:
    return {
        "title": "GPT-5가 멀티모달 워크로드의 지연 시간을 줄였습니다",
        "excerpt": "실사용 관점에서 지연 시간이 줄어들었고, 제품팀이 검토할 실무 포인트가 더 명확해졌습니다.",
        "focus_items": [
            "GPT-5는 멀티모달 추론 경로의 지연 시간을 줄였습니다.",
            "낮은 지연 시간은 인터랙티브 AI 제품의 비용과 설계를 바꿉니다.",
            "다음 공개 자료에서는 가격과 처리량 정보를 함께 봐야 합니다.",
        ],
        "guide_items": {
            "one_liner": "GPT-5는 더 빠른 멀티모달 추론을 목표로 한 모델 업데이트입니다.",
            "action_item": "현재 프롬프트를 새 지연 시간 프로파일과 비교 측정해보세요.",
            "critical_gotcha": "지연 시간 개선이 비용과 긴 문맥 성능까지 보장하는 것은 아닙니다.",
            "rotating_item": "긴 문맥 입력에서도 같은 속도 개선이 유지되는지가 핵심입니다.",
            "quiz_poll": {
                "question": "지연 시간 중심 모델 업데이트 후 가장 먼저 확인할 것은 무엇일까요?",
                "options": ["처리량", "신뢰성", "로고", "블로그 길이"],
                "answer": "B",
                "explanation": "실서비스에서는 속도보다 출력 신뢰성이 먼저 검증되어야 합니다.",
            },
        },
        "tags": ["gpt-5", "지연시간", "멀티모달"],
    }


def _make_ko_section(title: str, target_length: int) -> str:
    filler = "실제 적용 맥락과 기술적 근거를 함께 설명하는 한국어 번역 문장입니다. "
    body_length = max(target_length - len(title) - 1, 0)
    body = (filler * ((body_length // len(filler)) + 2))[:body_length]
    return f"{title}\n{body}"


def _make_business_en_post() -> dict:
    filler = "Business explanation with operational implications, competitive analysis, and buyer impact. "
    return {
        "title": "Anthropic expands enterprise AI financing",
        "slug": "2026-03-12-business-daily",
        "content_beginner": _make_markdown_sections(["## The Story"], 3400, filler),
        "content_learner": _make_markdown_sections(["## What Happened"], 3400, filler),
        "content_expert": _make_markdown_sections(["## Executive Summary"], 3400, filler),
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
        "source_urls": ["https://anthropic.com/news/example"],
        "news_temperature": 4,
        "tags": ["anthropic", "enterprise", "funding"],
    }


def _make_business_metadata_ko() -> dict:
    return {
        "title": "Anthropic가 엔터프라이즈 AI 투자 기반을 넓혔습니다",
        "excerpt": "이번 투자 라운드는 엔터프라이즈 고객이 플랫폼 리스크를 해석하는 방식에도 영향을 줍니다.",
        "focus_items": [
            "Anthropic는 제품과 연산 자원을 확장할 자본을 더 확보했습니다.",
            "엔터프라이즈 구매자는 재무 체력을 공급 안정성 신호로 읽습니다.",
            "다음으로는 가격 정책과 채용 확대가 실무적 신호가 됩니다.",
        ],
        "guide_items": {
            "one_liner": "Anthropic는 엔터프라이즈 AI 운영을 확대할 자본을 추가로 확보했습니다.",
            "action_item": "이번 분기에 단일 벤더 의존 가정을 다시 점검해보세요.",
            "critical_gotcha": "투자 규모가 비용 구조나 제품 실행력까지 보장하지는 않습니다.",
            "rotating_item": "대차대조표의 안정성은 벤치마크보다 먼저 구매자 신뢰에 영향을 줍니다.",
            "quiz_poll": {
                "question": "대규모 AI 투자 유치가 가장 먼저 바꾸는 것은 무엇일까요?",
                "options": ["연산 자원 접근성", "마스코트", "배경화면", "간식"],
                "answer": "A",
                "explanation": "큰 투자 라운드는 보통 연산 자원과 엔터프라이즈 실행 역량을 늘립니다.",
            },
        },
        "related_news": {
            "big_tech": None,
            "industry_biz": {
                "title": "OpenAI가 엔터프라이즈 번들을 확장했습니다",
                "url": "https://openai.com/blog/bundles",
                "summary": "대규모 팀이 AI를 도입할 때 검토할 수 있는 계약 옵션이 더 넓어졌습니다.",
            },
            "new_tools": None,
        },
        "tags": ["anthropic", "enterprise", "funding"],
    }


def test_split_markdown_sections_preserves_heading_order():
    from services.agents.translate import split_markdown_sections

    text = "## 1. First\nBody one\n\n## 2. Second\nBody two"

    assert split_markdown_sections(text) == [
        "## 1. First\nBody one",
        "## 2. Second\nBody two",
    ]


@pytest.mark.asyncio
async def test_translate_research_post_retries_short_section_and_preserves_structure():
    en_data = _make_research_en_post()
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(_make_research_metadata_ko()),
            _mock_openai_response({"translated_text": _make_ko_section("## 1. 무슨 일이 있었나", 320)}),
            _mock_openai_response({"translated_text": _make_ko_section("## 1. 무슨 일이 있었나", 1300)}),
            _mock_openai_response({"translated_text": _make_ko_section("## 2. 숫자로 보면", 1300)}),
            _mock_openai_response({"translated_text": _make_ko_section("## 3. 그래서 중요한 점", 1300)}),
            _mock_openai_response({"translated_text": _make_ko_section("## 4. 더 깊게 보기", 1300)}),
        ]
    )

    with patch("services.agents.translate.get_openai_client", return_value=mock_client):
        from services.agents.translate import translate_post

        result = await translate_post(en_data, "research")

    validated = ResearchPost.model_validate(result)

    assert validated.content_original is not None
    assert len(validated.content_original) >= RESEARCH_KO_MIN_CONTENT_CHARS
    assert validated.content_original.count("## ") == 4
    assert mock_client.chat.completions.create.await_count == 6

    retry_prompt = mock_client.chat.completions.create.await_args_list[2].kwargs["messages"][1]["content"]
    assert "previous translation was" in retry_prompt
    assert "minimum expected length" in retry_prompt


@pytest.mark.asyncio
async def test_translate_research_post_records_usage_metrics():
    en_data = _make_research_en_post()
    responses = [
        _mock_openai_response(_make_research_metadata_ko()),
        _mock_openai_response({"translated_text": _make_ko_section("## 1. 무슨 일이 있었나", 1300)}),
        _mock_openai_response({"translated_text": _make_ko_section("## 2. 숫자로 보면", 1300)}),
        _mock_openai_response({"translated_text": _make_ko_section("## 3. 그래서 중요한 점", 1300)}),
        _mock_openai_response({"translated_text": _make_ko_section("## 4. 더 깊게 보기", 1300)}),
    ]
    for index, call in enumerate(responses):
        call.usage = MagicMock(
            prompt_tokens=500 + (index * 50),
            completion_tokens=250 + (index * 25),
            total_tokens=750 + (index * 75),
        )

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=responses)

    usage = {}

    with patch("services.agents.translate.get_openai_client", return_value=mock_client):
        from services.agents.translate import translate_post

        result = await translate_post(en_data, "research", usage_recorder=usage)

    validated = ResearchPost.model_validate(result)

    assert validated.content_original is not None
    assert usage["tokens_used"] > 0
    assert usage["input_tokens"] > 0
    assert usage["output_tokens"] > 0
    assert usage["cost_usd"] is not None


@pytest.mark.asyncio
async def test_translate_research_no_news_skips_section_translation():
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
    metadata_ko = {
        "title": "오늘은 충분히 다른 리서치 업데이트가 없었습니다",
        "no_news_notice": "지난 24시간 동안 어제와 충분히 다른 AI 연구 업데이트는 확인되지 않았습니다.",
        "recent_fallback": "어제의 주요 흐름이 오늘 신호에서도 계속 우세했습니다.",
        "focus_items": [],
        "guide_items": None,
        "tags": ["no-news"],
    }
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response(metadata_ko)
    )

    with patch("services.agents.translate.get_openai_client", return_value=mock_client):
        from services.agents.translate import translate_post

        result = await translate_post(en_data, "research")

    validated = ResearchPost.model_validate(result)

    assert validated.has_news is False
    assert validated.content_original is None
    assert mock_client.chat.completions.create.await_count == 1


@pytest.mark.asyncio
async def test_translate_business_post_recovers_only_failing_field():
    en_data = _make_business_en_post()
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(_make_business_metadata_ko()),
            _mock_openai_response({"translated_text": _make_ko_section("## 이야기", 3300)}),
            _mock_openai_response({"translated_text": _make_ko_section("## 무슨 일이 있었나", 1400)}),
            _mock_openai_response({"translated_text": _make_ko_section("## 핵심 요약", 3300)}),
            _mock_openai_response({"translated_text": _make_ko_section("## 무슨 일이 있었나", 3300)}),
        ]
    )

    with patch("services.agents.translate.get_openai_client", return_value=mock_client):
        from services.agents.translate import translate_post

        result = await translate_post(en_data, "business")

    validated = BusinessPost.model_validate(result)

    assert len(validated.content_beginner) >= BUSINESS_KO_MIN_CONTENT_CHARS
    assert len(validated.content_learner) >= BUSINESS_KO_MIN_CONTENT_CHARS
    assert len(validated.content_expert) >= BUSINESS_KO_MIN_CONTENT_CHARS
    assert mock_client.chat.completions.create.await_count == 5

    prompts = [
        call.kwargs["messages"][1]["content"]
        for call in mock_client.chat.completions.create.await_args_list
    ]
    learner_recovery_prompts = [
        prompt
        for prompt in prompts
        if "content_learner" in prompt and "previous translation was" in prompt
    ]
    assert learner_recovery_prompts
    assert any(
        "minimum expected length for this translated section is" in prompt
        for prompt in learner_recovery_prompts
    )


def test_business_post_allows_shorter_korean_lengths():
    analysis = _make_ko_section("## 핵심 분석", BUSINESS_KO_MIN_ANALYSIS_CHARS + 73)
    beginner = _make_ko_section("## 이야기", BUSINESS_KO_MIN_CONTENT_CHARS + 93)
    learner = _make_ko_section("## 무슨 일이 있었나", BUSINESS_KO_MIN_CONTENT_CHARS + 183)
    expert = _make_ko_section("## 실행 요약", BUSINESS_KO_MIN_CONTENT_CHARS + 220)

    post = BusinessPost.model_validate(
        {
            "title": "Legora, 미국 확장을 위해 대규모 자금 조달",
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

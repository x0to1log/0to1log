import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.ranking import RankedCandidate
from models.research import EN_MIN_CONTENT_CHARS, KO_MIN_CONTENT_CHARS, ResearchPost


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    import httpx

    def _blocked(*args, **kwargs):
        raise RuntimeError("Real network call blocked in tests!")

    monkeypatch.setattr(httpx.AsyncClient, "send", _blocked)
    monkeypatch.setattr(httpx.Client, "send", _blocked)


def _mock_openai_response(data: dict) -> MagicMock:
    choice = MagicMock()
    choice.message.content = json.dumps(data)
    response = MagicMock()
    response.choices = [choice]
    return response


def _make_content(target_length: int) -> str:
    section_titles = [
        "## 1. What Happened",
        "## 2. By the Numbers",
        "## 3. So What - Practical Implications",
        "## 4. Deep Dive - Sources and Code",
    ]
    filler = "Technical detail with source-backed analysis and implementation context. "
    available = max(target_length - sum(len(title) + 2 for title in section_titles), 4800)
    per_section = available // len(section_titles)
    remainder = available % len(section_titles)
    sections = []

    for index, title in enumerate(section_titles):
        length = per_section + (1 if index < remainder else 0)
        body = (filler * ((length // len(filler)) + 2))[:length]
        sections.append(f"{title}\n{body}")

    return "\n\n".join(sections)


def _make_ko_content(target_length: int) -> str:
    section_titles = [
        "## 1. 무슨 일이 있었나",
        "## 2. 숫자로 보면",
        "## 3. 그래서 왜 중요한가",
        "## 4. 더 깊게 보기",
    ]
    filler = "기술적 맥락과 실제 적용 포인트를 근거 중심으로 설명하는 한국어 문장입니다. "
    available = max(target_length - sum(len(title) + 2 for title in section_titles), 3600)
    per_section = available // len(section_titles)
    remainder = available % len(section_titles)
    sections = []

    for index, title in enumerate(section_titles):
        length = per_section + (1 if index < remainder else 0)
        body = (filler * ((length // len(filler)) + 2))[:length]
        sections.append(f"{title}\n{body}")

    return "\n\n".join(sections)


def _make_research_response(content_length: int) -> dict:
    return {
        "has_news": True,
        "title": "GPT-5 released with lower latency",
        "slug": "2026-03-12-research-daily",
        "content_original": _make_content(content_length),
        "excerpt": "OpenAI shipped a faster model update with clearer practical tradeoffs for production teams.",
        "focus_items": [
            "GPT-5 reduced end-to-end latency on interactive workloads.",
            "Faster responses change how teams budget user-facing AI features.",
            "Watch for pricing and throughput disclosures in the next API update.",
        ],
        "guide_items": {
            "one_liner": "GPT-5 is a faster general-purpose model update for production inference.",
            "action_item": "Compare latency and output stability against your current GPT-4o prompts.",
            "critical_gotcha": "Latency gains do not guarantee lower cost or better long-context behavior.",
            "rotating_item": "Benchmark wins matter less than reliability under your real workload.",
            "quiz_poll": {
                "question": "What should teams validate first after a latency-focused model release?",
                "options": ["Cost", "Reliability", "Fine-tuning support", "Logo refresh"],
                "answer": "B",
                "explanation": "Lower latency is useful only if the outputs stay reliable in production.",
            },
        },
        "source_urls": ["https://openai.com/blog/example"],
        "news_temperature": 4,
        "tags": ["gpt-5", "latency", "production-ai"],
    }


def test_research_post_accepts_ko_4000_char_minimum():
    valid_response = _make_research_response(4099)
    valid_response["content_original"] = _make_ko_content(4099)

    post = ResearchPost.model_validate(valid_response)

    assert post.content_original is not None
    assert len(post.content_original) >= KO_MIN_CONTENT_CHARS


def test_research_post_accepts_5000_char_minimum():
    valid_response = _make_research_response(5461)

    post = ResearchPost.model_validate(valid_response)

    assert post.content_original is not None
    assert len(post.content_original) >= EN_MIN_CONTENT_CHARS


@pytest.mark.asyncio
async def test_generate_research_post_retries_with_8000_char_target_feedback():
    short_response = _make_research_response(4990)
    short_length = len(short_response["content_original"])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(short_response),
            _mock_openai_response(short_response),
            _mock_openai_response(short_response),
            _mock_openai_response(_make_research_response(8125)),
        ]
    )

    candidate = RankedCandidate(
        title="GPT-5 Released",
        url="https://openai.com/blog/example",
        snippet="OpenAI released a faster flagship model.",
        source="tavily",
        assigned_type="research",
        relevance_score=0.95,
        ranking_reason="Major model release with production impact",
    )

    with patch("services.agents.research.get_openai_client", return_value=mock_client):
        from services.agents.research import generate_research_post

        result = await generate_research_post(
            candidate=candidate,
            context="Collected research context",
            batch_id="2026-03-12",
        )

    assert isinstance(result, ResearchPost)
    assert result.content_original is not None
    assert len(result.content_original) >= EN_MIN_CONTENT_CHARS
    assert mock_client.chat.completions.create.await_count == 4

    second_prompt = mock_client.chat.completions.create.await_args_list[1].kwargs["messages"][1]["content"]
    assert f"{short_length} chars" in second_prompt
    assert str(EN_MIN_CONTENT_CHARS - short_length) in second_prompt
    assert "target at least 8000 chars" in second_prompt


@pytest.mark.asyncio
async def test_generate_research_post_expands_to_safe_translation_floor():
    initial_response = _make_research_response(5001)
    expanded_response = _make_research_response(6900)
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(initial_response),
            _mock_openai_response(expanded_response),
        ]
    )

    candidate = RankedCandidate(
        title="GPT-5 Released",
        url="https://openai.com/blog/example",
        snippet="OpenAI released a faster flagship model.",
        source="tavily",
        assigned_type="research",
        relevance_score=0.95,
        ranking_reason="Major model release with production impact",
    )

    with patch("services.agents.research.get_openai_client", return_value=mock_client):
        from services.agents.research import SAFE_TRANSLATION_FLOOR, generate_research_post

        result = await generate_research_post(
            candidate=candidate,
            context="Collected research context",
            batch_id="2026-03-12",
        )

    assert isinstance(result, ResearchPost)
    assert len(result.content_original or "") >= SAFE_TRANSLATION_FLOOR
    assert mock_client.chat.completions.create.await_count == 2

    safe_floor_prompt = mock_client.chat.completions.create.await_args_list[1].kwargs["messages"][1]["content"]
    assert f"expand it to at least {SAFE_TRANSLATION_FLOOR} chars" in safe_floor_prompt

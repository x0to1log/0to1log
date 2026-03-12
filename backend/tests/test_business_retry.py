import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.business import MIN_CONTENT_CHARS, BusinessPost
from models.ranking import RankedCandidate, RelatedPicks


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


def _make_persona_content(target_length: int, heading: str) -> str:
    filler = (
        "Business context with concrete market dynamics, pricing pressure, "
        "distribution strategy, and operational tradeoffs. "
    )
    body_length = max(target_length - len(heading) - 1, 0)
    body = (filler * ((body_length // len(filler)) + 2))[:body_length]
    return f"{heading}\n{body}"


def _make_business_response(persona_length: int) -> dict:
    return {
        "title": "Anthropic raises new funding round",
        "slug": "2026-03-12-business-daily",
        "content_beginner": _make_persona_content(persona_length, "## The Story"),
        "content_learner": _make_persona_content(persona_length, "## What Happened"),
        "content_expert": _make_persona_content(persona_length, "## Executive Summary"),
        "excerpt": "Anthropic's new funding changes how teams should think about AI platform competition.",
        "focus_items": [
            "Anthropic secured a major funding round tied to continued model expansion.",
            "Capital strength changes go-to-market leverage and enterprise confidence.",
            "Watch how pricing, hiring, and capacity announcements follow this raise.",
        ],
        "guide_items": {
            "one_liner": "Anthropic raised more money to accelerate model development and enterprise growth.",
            "action_item": "Review whether your roadmap depends too heavily on a single model vendor.",
            "critical_gotcha": "Funding scale does not guarantee inference quality, margin, or customer retention.",
            "rotating_item": "The financing signal matters because buyers treat balance-sheet strength as product risk reduction.",
            "quiz_poll": {
                "question": "What does a large funding round most directly buy first for an AI company?",
                "options": ["Datacenter access", "Office plants", "Logo redesign", "Snack budget"],
                "answer": "A",
                "explanation": "Large rounds often translate into compute access, hiring, and enterprise go-to-market execution.",
            },
        },
        "related_news": {
            "big_tech": None,
            "industry_biz": {
                "title": "OpenAI expands enterprise pricing tiers",
                "url": "https://openai.com/blog/example",
                "summary": "OpenAI introduced new pricing bundles for large customers evaluating multi-team deployments.",
            },
            "new_tools": None,
        },
        "source_urls": ["https://anthropic.com/news/example"],
        "news_temperature": 4,
        "tags": ["anthropic", "funding", "enterprise-ai"],
    }


@pytest.mark.asyncio
async def test_generate_business_post_retries_with_field_lengths_and_target_range():
    short_response = _make_business_response(2890)
    short_lengths = {
        "content_beginner": len(short_response["content_beginner"]),
        "content_learner": len(short_response["content_learner"]),
        "content_expert": len(short_response["content_expert"]),
    }
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(short_response),
            _mock_openai_response(short_response),
            _mock_openai_response(short_response),
            _mock_openai_response(_make_business_response(MIN_CONTENT_CHARS + 1400)),
        ]
    )

    candidate = RankedCandidate(
        title="Anthropic raises funding",
        url="https://anthropic.com/news/example",
        snippet="Anthropic secured another major funding round.",
        source="tavily",
        assigned_type="business_main",
        relevance_score=0.91,
        ranking_reason="Large funding round with enterprise AI implications",
    )
    related = RelatedPicks()

    with patch("services.agents.business.get_openai_client", return_value=mock_client):
        from services.agents.business import generate_business_post

        result = await generate_business_post(
            candidate=candidate,
            related=related,
            context="Collected business context",
            batch_id="2026-03-12",
        )

    assert isinstance(result, BusinessPost)
    assert len(result.content_beginner) >= MIN_CONTENT_CHARS
    assert len(result.content_learner) >= MIN_CONTENT_CHARS
    assert len(result.content_expert) >= MIN_CONTENT_CHARS
    assert mock_client.chat.completions.create.await_count == 4

    second_prompt = mock_client.chat.completions.create.await_args_list[1].kwargs["messages"][1]["content"]
    assert f"content_beginner was {short_lengths['content_beginner']} chars" in second_prompt
    assert f"content_learner was {short_lengths['content_learner']} chars" in second_prompt
    assert f"content_expert was {short_lengths['content_expert']} chars" in second_prompt
    assert "target 4000-5000 chars per persona" in second_prompt

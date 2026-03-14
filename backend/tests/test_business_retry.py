"""Tests for business post generation retry logic — v4 Expert-First 2-Call Cascade."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.business import MIN_ANALYSIS_CHARS, MIN_CONTENT_CHARS, BusinessPost
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
    response.usage = MagicMock(
        prompt_tokens=800,
        completion_tokens=400,
        total_tokens=1200,
    )
    return response


def _make_persona_content(target_length: int, heading: str) -> str:
    filler = (
        "Business context with concrete market dynamics, pricing pressure, "
        "distribution strategy, and operational tradeoffs. "
    )
    body_length = max(target_length - len(heading) - 1, 0)
    body = (filler * ((body_length // len(filler)) + 2))[:body_length]
    return f"{heading}\n{body}"


def _make_expert_response(analysis_length: int = None, expert_length: int = None) -> dict:
    """Build a Call 1 (expert) response with configurable lengths."""
    al = analysis_length if analysis_length is not None else max(MIN_ANALYSIS_CHARS, 2800)
    el = expert_length if expert_length is not None else MIN_CONTENT_CHARS + 1400
    return {
        "title": "Anthropic raises new funding round",
        "slug": "2026-03-12-business-daily",
        "content_analysis": _make_persona_content(al, "## Core Analysis"),
        "content_expert": _make_persona_content(el, "## Executive Summary"),
        "fact_pack": {
            "key_facts": ["Anthropic secured a new funding round."],
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
                "evidence_snippet": "Official announcement of the funding round.",
                "claim_ids": ["claim-1"],
            }
        ],
        "excerpt": "Anthropic's new funding changes how teams should think about AI platform competition.",
        "focus_items": [
            "Anthropic secured a major funding round tied to continued model expansion.",
            "Capital strength changes go-to-market leverage and enterprise confidence.",
            "Watch how pricing, hiring, and capacity announcements follow this raise.",
        ],
        "guide_items": {
            "one_liner": "Anthropic raised more money to accelerate model development.",
            "action_item": "Review whether your roadmap depends too heavily on a single model vendor.",
            "critical_gotcha": "Funding scale does not guarantee inference quality or customer retention.",
            "rotating_item": "The financing signal matters because buyers treat balance-sheet strength as risk reduction.",
            "quiz_poll": {
                "question": "What does a large funding round most directly buy first?",
                "options": ["Datacenter access", "Office plants", "Logo redesign", "Snack budget"],
                "answer": "A",
                "explanation": "Large rounds translate into compute access, hiring, and enterprise execution.",
            },
        },
        "related_news": {
            "big_tech": None,
            "industry_biz": {
                "title": "OpenAI expands enterprise pricing tiers",
                "url": "https://openai.com/blog/example",
                "summary": "OpenAI introduced new pricing bundles for large customers.",
            },
            "new_tools": None,
        },
        "source_urls": ["https://anthropic.com/news/example"],
        "news_temperature": 4,
        "tags": ["anthropic", "funding", "enterprise-ai"],
    }


def _make_derive_response(learner_length: int = None, beginner_length: int = None) -> dict:
    """Build a Call 2 (derive) response with configurable lengths."""
    ll = learner_length if learner_length is not None else MIN_CONTENT_CHARS + 1400
    bl = beginner_length if beginner_length is not None else MIN_CONTENT_CHARS + 1400
    return {
        "content_learner": _make_persona_content(ll, "## What Happened"),
        "content_beginner": _make_persona_content(bl, "## The Story"),
    }


CANDIDATE = RankedCandidate(
    title="Anthropic raises funding",
    url="https://anthropic.com/news/example",
    snippet="Anthropic secured another major funding round.",
    source="tavily",
    assigned_type="business_main",
    relevance_score=0.91,
    ranking_reason="Large funding round with enterprise AI implications",
)


@pytest.mark.asyncio
async def test_generate_business_expert_retries_on_short_analysis():
    """Call 1 retries when analysis or expert content is too short."""
    short_expert = _make_expert_response(analysis_length=1200, expert_length=2000)
    good_expert = _make_expert_response()
    good_derive = _make_derive_response()

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(short_expert),   # Call 1 attempt 1: too short
            _mock_openai_response(good_expert),     # Call 1 attempt 2: OK
            _mock_openai_response(good_derive),     # Call 2: OK
        ]
    )

    with patch("services.agents.business.get_openai_client", return_value=mock_client):
        from services.agents.business import generate_business_post

        result, usage, _, _ = await generate_business_post(
            candidate=CANDIDATE,
            related=RelatedPicks(),
            context="Collected business context",
            batch_id="2026-03-12",
        )

    assert isinstance(result, BusinessPost)
    assert len(result.content_analysis) >= MIN_ANALYSIS_CHARS
    assert len(result.content_expert) >= MIN_CONTENT_CHARS
    # 2 attempts for expert + 1 for derive = 3 total calls
    assert mock_client.chat.completions.create.await_count == 3

    retry_prompt = mock_client.chat.completions.create.await_args_list[1].kwargs["messages"][1]["content"]
    assert "content_analysis" in retry_prompt
    assert "too short" in retry_prompt.lower()


@pytest.mark.asyncio
async def test_generate_business_expert_fails_after_max_retries():
    """Call 1 raises ValueError if analysis stays too short after all retries."""
    short_expert = _make_expert_response(analysis_length=1200, expert_length=2000)

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response(short_expert)
    )

    with patch("services.agents.business.get_openai_client", return_value=mock_client):
        from services.agents.business import generate_business_post

        with pytest.raises(ValueError, match="BusinessExpert failed"):
            await generate_business_post(
                candidate=CANDIDATE,
                related=RelatedPicks(),
                context="Collected business context",
                batch_id="2026-03-12",
            )

    # 1 initial + 2 retries = 3 total calls (all for Call 1, never reaches Call 2)
    assert mock_client.chat.completions.create.await_count == 3


@pytest.mark.asyncio
async def test_derive_business_personas_retries_on_short_content():
    """Call 2 retries when learner or beginner content is too short."""
    good_expert = _make_expert_response()
    short_derive = _make_derive_response(learner_length=2000, beginner_length=2000)
    good_derive = _make_derive_response()

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(good_expert),     # Call 1: OK
            _mock_openai_response(short_derive),     # Call 2 attempt 1: too short
            _mock_openai_response(good_derive),      # Call 2 attempt 2: OK
        ]
    )

    with patch("services.agents.business.get_openai_client", return_value=mock_client):
        from services.agents.business import generate_business_post

        result, _, _, _ = await generate_business_post(
            candidate=CANDIDATE,
            related=RelatedPicks(),
            context="Collected business context",
            batch_id="2026-03-12",
        )

    assert isinstance(result, BusinessPost)
    assert len(result.content_learner) >= MIN_CONTENT_CHARS
    assert len(result.content_beginner) >= MIN_CONTENT_CHARS
    # 1 for expert + 2 for derive = 3 total calls
    assert mock_client.chat.completions.create.await_count == 3

"""Tests for business post generation — v4 Expert-First 2-Call Cascade."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.business import BusinessPost
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
    choice.message.content = json.dumps(data, ensure_ascii=False)
    response = MagicMock()
    response.choices = [choice]
    response.usage = MagicMock(
        prompt_tokens=800,
        completion_tokens=400,
        total_tokens=1200,
    )
    return response


def _long_markdown(heading: str, sentence: str, repeats: int) -> str:
    return f"{heading}\n" + (sentence * repeats)


def _make_expert_response() -> dict:
    """Call 1 response: expert + metadata + fact_pack + source_cards."""
    return {
        "title": "OpenAI expands enterprise bundles",
        "slug": "2026-03-12-business-daily",
        "fact_pack": {
            "key_facts": ["OpenAI launched a broader enterprise bundle."],
            "numbers": ["Bundle pricing details pending."],
            "entities": ["OpenAI", "Enterprise AI"],
            "timeline": ["2026-Q1 — Enterprise bundle announced."],
        },
        "source_cards": [
            {
                "id": "src-1",
                "title": "OpenAI launches enterprise bundle",
                "publisher": "OpenAI",
                "url": "https://openai.com/blog/enterprise-bundle",
                "published_at": "2026-03-12T00:00:00Z",
                "evidence_snippet": "Official announcement with plan details.",
                "claim_ids": ["claim-1"],
            }
        ],
        "content_analysis": _long_markdown(
            "## Core Analysis",
            "Shared market analysis with cost, buyer, and integration detail. ",
            80,
        ),
        "content_expert": _long_markdown(
            "## Executive Summary",
            "Expert-facing insight with market structure and deployment risk detail. ",
            100,
        ),
        "excerpt": "OpenAI's new bundle changes how enterprise buyers compare AI vendors.",
        "focus_items": [
            "OpenAI changed enterprise packaging.",
            "Bundle changes alter procurement dynamics.",
            "Watch contract and pricing disclosures next.",
        ],
        "guide_items": {
            "one_liner": "OpenAI packaged more enterprise AI capabilities together.",
            "action_item": "Review how bundle terms affect vendor comparisons.",
            "critical_gotcha": "Bundling can hide cost growth inside broader contracts.",
            "rotating_item": "Package changes often move procurement faster than raw benchmark gains.",
            "quiz_poll": {
                "question": "What changes first when enterprise bundles improve?",
                "options": ["Procurement framing", "Office snacks", "Logo color"],
                "answer": "A",
                "explanation": "Packaging changes how buyers justify and compare purchases.",
            },
        },
        "related_news": {
            "big_tech": None,
            "industry_biz": None,
            "new_tools": None,
        },
        "source_urls": ["https://openai.com/blog/enterprise-bundle"],
        "news_temperature": 4,
        "tags": ["enterprise", "pricing"],
    }


def _make_derive_response() -> dict:
    """Call 2 response: learner + beginner derived from expert."""
    return {
        "content_learner": _long_markdown("## What Happened", "Learner-facing insight with context and detailed explanation of market dynamics. ", 70),
        "content_beginner": _long_markdown("## The Story", "Beginner-facing insight with context and real-world examples for understanding. ", 70),
    }


@pytest.mark.asyncio
async def test_generate_business_post_builds_fact_pack_analysis_and_personas():
    """v4: 2-call cascade produces fact_pack, analysis, and 3 personas."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(_make_expert_response()),
            _mock_openai_response(_make_derive_response()),
        ]
    )

    candidate = RankedCandidate(
        title="OpenAI enterprise bundle",
        url="https://openai.com/blog/enterprise-bundle",
        snippet="OpenAI broadened enterprise packaging.",
        source="tavily",
        assigned_type="business_main",
        relevance_score=0.94,
        ranking_reason="Enterprise packaging shift with buyer impact",
    )

    with patch("services.agents.business.get_openai_client", return_value=mock_client):
        from services.agents.business import generate_business_post

        result, usage, _, _ = await generate_business_post(candidate, RelatedPicks(), "Context", "2026-03-12")

    assert isinstance(result, BusinessPost)
    assert result.content_analysis.startswith("## Core Analysis")
    assert "OpenAI launched a broader enterprise bundle." in result.fact_pack["key_facts"]
    assert result.source_cards[0]["publisher"] == "OpenAI"
    # v4: exactly 2 calls (expert + derive)
    assert mock_client.chat.completions.create.await_count == 2
    assert usage["tokens_used"] > 0


@pytest.mark.asyncio
async def test_generate_business_post_returns_all_three_personas():
    """v4: expert from Call 1, learner + beginner from Call 2."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(_make_expert_response()),
            _mock_openai_response(_make_derive_response()),
        ]
    )

    candidate = RankedCandidate(
        title="OpenAI enterprise bundle",
        url="https://openai.com/blog/enterprise-bundle",
        snippet="OpenAI broadened enterprise packaging.",
        source="tavily",
        assigned_type="business_main",
        relevance_score=0.94,
        ranking_reason="Enterprise packaging shift with buyer impact",
    )

    with patch("services.agents.business.get_openai_client", return_value=mock_client):
        from services.agents.business import generate_business_post

        result, _, _, _ = await generate_business_post(candidate, RelatedPicks(), "Context", "2026-03-12")

    assert result.content_expert.startswith("## Executive Summary")
    assert result.content_learner.startswith("## What Happened")
    assert result.content_beginner.startswith("## The Story")
    # All three should be distinct
    assert result.content_expert != result.content_learner
    assert result.content_learner != result.content_beginner

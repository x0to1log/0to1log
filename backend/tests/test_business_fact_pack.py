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
    return response


def _long_markdown(heading: str, sentence: str, repeats: int) -> str:
    return f"{heading}\n" + (sentence * repeats)


@pytest.mark.asyncio
async def test_generate_business_post_builds_fact_pack_analysis_and_personas():
    fact_pack = {
        "fact_pack": [
            {
                "id": "claim-1",
                "claim": "OpenAI launched a broader enterprise bundle. [[1]]",
                "why_it_matters": "Larger bundles change procurement framing.",
                "source_ids": ["src-1"],
                "confidence": "high",
            }
        ],
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
    }
    analysis = {
        "title": "OpenAI expands enterprise bundles",
        "slug": "2026-03-12-business-daily",
        "content_analysis": _long_markdown(
            "## Core Analysis",
            "Shared market analysis with cost, buyer, and integration detail. [[1]] ",
            80,
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
    beginner = {"content_beginner": _long_markdown("## The Story", "Beginner-facing insight with context. ", 120)}
    learner = {"content_learner": _long_markdown("## What Happened", "Learner-facing insight with context. ", 120)}
    expert = {"content_expert": _long_markdown("## Executive Summary", "Expert-facing insight with context. ", 120)}

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(fact_pack),
            _mock_openai_response(analysis),
            _mock_openai_response(beginner),
            _mock_openai_response(learner),
            _mock_openai_response(expert),
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

        result = await generate_business_post(candidate, RelatedPicks(), "Context", "2026-03-12")

    assert isinstance(result, BusinessPost)
    assert result.content_analysis.startswith("## Core Analysis")
    assert result.fact_pack[0].claim.endswith("[[1]]")
    assert result.source_cards[0].publisher == "OpenAI"
    assert mock_client.chat.completions.create.await_count == 5


@pytest.mark.asyncio
async def test_generate_business_post_emits_stage_logs_for_fact_pack_analysis_and_personas():
    fact_pack = {
        "fact_pack": [
            {
                "id": "claim-1",
                "claim": "OpenAI launched a broader enterprise bundle. [[1]]",
                "why_it_matters": "Larger bundles change procurement framing.",
                "source_ids": ["src-1"],
                "confidence": "high",
            }
        ],
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
    }
    analysis = {
        "title": "OpenAI expands enterprise bundles",
        "slug": "2026-03-12-business-daily",
        "content_analysis": _long_markdown(
            "## Core Analysis",
            "Shared market analysis with cost, buyer, and integration detail. [[1]] ",
            80,
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
        "related_news": {"big_tech": None, "industry_biz": None, "new_tools": None},
        "source_urls": ["https://openai.com/blog/enterprise-bundle"],
        "news_temperature": 4,
        "tags": ["enterprise", "pricing"],
    }

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(fact_pack),
            _mock_openai_response(analysis),
            _mock_openai_response({"content_beginner": _long_markdown("## The Story", "Beginner-facing insight. ", 180)}),
            _mock_openai_response({"content_learner": _long_markdown("## What Happened", "Learner-facing insight. ", 180)}),
            _mock_openai_response({"content_expert": _long_markdown("## Executive Summary", "Expert-facing insight. ", 180)}),
        ]
    )

    events = []

    def stage_logger(stage_name, status, attempt, debug_meta, output_summary):
        events.append(
            {
                "stage_name": stage_name,
                "status": status,
                "attempt": attempt,
                "debug_meta": debug_meta or {},
                "output_summary": output_summary,
            }
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

        await generate_business_post(
            candidate,
            RelatedPicks(),
            "Context",
            "2026-03-12",
            stage_logger=stage_logger,
        )

    stage_names = [event["stage_name"] for event in events]
    assert stage_names == [
        "business.fact_pack.en",
        "business.analysis.en",
        "business.persona.beginner.en",
        "business.persona.learner.en",
        "business.persona.expert.en",
    ]
    assert all(event["status"] == "success" for event in events)

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
        "content_analysis": _make_persona_content(max(MIN_ANALYSIS_CHARS, 2400), "## Core Analysis"),
        "content_beginner": _make_persona_content(persona_length, "## The Story"),
        "content_learner": _make_persona_content(persona_length, "## What Happened"),
        "content_expert": _make_persona_content(persona_length, "## Executive Summary"),
        "fact_pack": [
            {
                "id": "claim-1",
                "claim": "Anthropic secured a new funding round. [[1]]",
                "why_it_matters": "Funding depth affects buyer trust and compute access.",
                "source_ids": ["src-1"],
                "confidence": "high",
            }
        ],
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
    }
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response({
                "fact_pack": short_response["fact_pack"],
                "source_cards": short_response["source_cards"],
            }),
            _mock_openai_response({
                key: short_response[key]
                for key in (
                    "title",
                    "slug",
                    "content_analysis",
                    "excerpt",
                    "focus_items",
                    "guide_items",
                    "related_news",
                    "source_urls",
                    "news_temperature",
                    "tags",
                )
            }),
            _mock_openai_response({"content_beginner": short_response["content_beginner"]}),
            _mock_openai_response({"content_beginner": short_response["content_beginner"]}),
            _mock_openai_response({"content_beginner": short_response["content_beginner"]}),
            _mock_openai_response({"content_beginner": _make_business_response(MIN_CONTENT_CHARS + 1400)["content_beginner"]}),
            _mock_openai_response({"content_learner": _make_business_response(MIN_CONTENT_CHARS + 1400)["content_learner"]}),
            _mock_openai_response({"content_expert": _make_business_response(MIN_CONTENT_CHARS + 1400)["content_expert"]}),
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
    assert len(result.content_analysis) >= MIN_ANALYSIS_CHARS
    assert len(result.content_beginner) >= MIN_CONTENT_CHARS
    assert len(result.content_learner) >= MIN_CONTENT_CHARS
    assert len(result.content_expert) >= MIN_CONTENT_CHARS
    assert mock_client.chat.completions.create.await_count == 8

    retry_prompt = mock_client.chat.completions.create.await_args_list[3].kwargs["messages"][1]["content"]
    assert f"content_beginner was {short_lengths['content_beginner']} chars" in retry_prompt
    assert "minimum required is 3000 chars" in retry_prompt
    assert "target 4000-5000 chars" in retry_prompt


@pytest.mark.asyncio
async def test_generate_business_post_fails_fast_when_analysis_stays_too_short():
    short_analysis = "## Core Analysis\n" + ("Too short. " * 120)
    complete_payload = _make_business_response(MIN_CONTENT_CHARS + 200)
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(
                {
                    "fact_pack": complete_payload["fact_pack"],
                    "source_cards": complete_payload["source_cards"],
                }
            ),
            _mock_openai_response(
                {
                    "title": complete_payload["title"],
                    "slug": complete_payload["slug"],
                    "content_analysis": short_analysis,
                    "excerpt": complete_payload["excerpt"],
                    "focus_items": complete_payload["focus_items"],
                    "guide_items": complete_payload["guide_items"],
                    "related_news": complete_payload["related_news"],
                    "source_urls": complete_payload["source_urls"],
                    "news_temperature": complete_payload["news_temperature"],
                    "tags": complete_payload["tags"],
                }
            ),
            _mock_openai_response(
                {
                    "title": complete_payload["title"],
                    "slug": complete_payload["slug"],
                    "content_analysis": short_analysis,
                    "excerpt": complete_payload["excerpt"],
                    "focus_items": complete_payload["focus_items"],
                    "guide_items": complete_payload["guide_items"],
                    "related_news": complete_payload["related_news"],
                    "source_urls": complete_payload["source_urls"],
                    "news_temperature": complete_payload["news_temperature"],
                    "tags": complete_payload["tags"],
                }
            ),
            _mock_openai_response(
                {
                    "title": complete_payload["title"],
                    "slug": complete_payload["slug"],
                    "content_analysis": short_analysis,
                    "excerpt": complete_payload["excerpt"],
                    "focus_items": complete_payload["focus_items"],
                    "guide_items": complete_payload["guide_items"],
                    "related_news": complete_payload["related_news"],
                    "source_urls": complete_payload["source_urls"],
                    "news_temperature": complete_payload["news_temperature"],
                    "tags": complete_payload["tags"],
                }
            ),
            _mock_openai_response(
                {
                    "title": complete_payload["title"],
                    "slug": complete_payload["slug"],
                    "content_analysis": short_analysis,
                    "excerpt": complete_payload["excerpt"],
                    "focus_items": complete_payload["focus_items"],
                    "guide_items": complete_payload["guide_items"],
                    "related_news": complete_payload["related_news"],
                    "source_urls": complete_payload["source_urls"],
                    "news_temperature": complete_payload["news_temperature"],
                    "tags": complete_payload["tags"],
                }
            ),
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
    artifact_recorder = MagicMock()

    with patch("services.agents.business.get_openai_client", return_value=mock_client):
        from services.agents.business import generate_business_post

        with pytest.raises(Exception, match="Business analysis too short"):
            await generate_business_post(
                candidate=candidate,
                related=RelatedPicks(),
                context="Collected business context",
                batch_id="2026-03-12",
                artifact_recorder=artifact_recorder,
            )

    assert mock_client.chat.completions.create.await_count == 5
    assert artifact_recorder.call_count == 2
    latest_partial_state, latest_status, latest_failed_stage, latest_error = artifact_recorder.call_args.args
    assert latest_status == "partial"
    assert latest_failed_stage == "business.analysis.en"
    assert "Business analysis too short" in latest_error
    assert latest_partial_state["fact_pack"] == complete_payload["fact_pack"]
    assert latest_partial_state["analysis_data"] == {}


@pytest.mark.asyncio
async def test_generate_business_post_resumes_from_partial_state_and_only_generates_missing_personas():
    completed = _make_business_response(MIN_CONTENT_CHARS + 1200)
    partial_state = {
        "fact_pack": completed["fact_pack"],
        "source_cards": completed["source_cards"],
        "analysis_data": {
            key: completed[key]
            for key in (
                "title",
                "slug",
                "content_analysis",
                "excerpt",
                "focus_items",
                "guide_items",
                "related_news",
                "source_urls",
                "news_temperature",
                "tags",
            )
        },
        "persona_payloads": {
            "beginner": {"content_beginner": completed["content_beginner"]},
        },
        "completed_stages": [
            "business.fact_pack.en",
            "business.analysis.en",
            "business.persona.beginner.en",
        ],
    }
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response({"content_learner": completed["content_learner"]}),
            _mock_openai_response({"content_expert": completed["content_expert"]}),
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
    artifact_recorder = MagicMock()

    with patch("services.agents.business.get_openai_client", return_value=mock_client):
        from services.agents.business import generate_business_post

        result = await generate_business_post(
            candidate=candidate,
            related=RelatedPicks(),
            context="Collected business context",
            batch_id="2026-03-12",
            partial_state=partial_state,
            artifact_recorder=artifact_recorder,
        )

    assert isinstance(result, BusinessPost)
    assert result.content_beginner == completed["content_beginner"]
    assert result.content_learner == completed["content_learner"]
    assert result.content_expert == completed["content_expert"]
    assert mock_client.chat.completions.create.await_count == 2
    assert artifact_recorder.call_count == 2
    final_partial_state, final_status, final_failed_stage, final_error = artifact_recorder.call_args.args
    assert final_status == "partial"
    assert final_failed_stage is None
    assert final_error is None
    assert final_partial_state["completed_stages"] == [
        "business.fact_pack.en",
        "business.analysis.en",
        "business.persona.beginner.en",
        "business.persona.learner.en",
        "business.persona.expert.en",
    ]

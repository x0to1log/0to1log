"""Tests for LLM persona writer agent."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.news_pipeline import FactPack, PersonaOutput


def _mock_openai_response(data: dict, tokens: int = 2000):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = json.dumps(data)
    mock_resp.usage = MagicMock()
    mock_resp.usage.prompt_tokens = 3000
    mock_resp.usage.completion_tokens = tokens
    mock_resp.usage.total_tokens = 3000 + tokens
    return mock_resp


SAMPLE_FACT_PACK = FactPack.model_validate({
    "headline": "OpenAI releases GPT-5",
    "key_facts": [
        {"id": "f1", "claim": "GPT-5 scores 95% on MMLU", "why_it_matters": "Big improvement", "source_ids": ["s1"], "confidence": "high"},
    ],
    "numbers": [{"value": "95%", "context": "MMLU", "source_id": "s1"}],
    "entities": [{"name": "OpenAI", "role": "developer", "url": "https://openai.com"}],
    "sources": [{"id": "s1", "title": "OpenAI Blog", "publisher": "openai.com", "url": "https://openai.com/blog/gpt5", "published_at": "2026-03-15"}],
    "community_summary": "Mixed reactions.",
})

EXPERT_OUTPUT = {
    "en": "## Executive Summary\nGPT-5 achieves 95% on MMLU. " + "x" * 3000,
    "ko": "## 핵심 요약\nGPT-5가 MMLU 95%를 달성. " + "가" * 3000,
}

LEARNER_OUTPUT = {
    "en": "## What Happened\nOpenAI released GPT-5. " + "y" * 3000,
    "ko": "## 무슨 일이 있었나\nOpenAI가 GPT-5를 출시. " + "나" * 3000,
}

@pytest.mark.asyncio
async def test_write_persona_expert():
    """Expert persona returns EN+KO content."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(EXPERT_OUTPUT)

    with patch("services.agents.persona_writer.get_openai_client", return_value=mock_client), \
         patch("services.agents.persona_writer.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.persona_writer import write_persona
        output, usage = await write_persona(
            persona="expert",
            fact_pack=SAMPLE_FACT_PACK,
            handbook_slugs=["transformer", "llm"],
        )

    assert "Executive Summary" in output.en
    assert "핵심 요약" in output.ko
    assert usage["tokens_used"] > 0


@pytest.mark.asyncio
async def test_write_all_personas_parallel():
    """write_all_personas runs 2 personas (expert + learner) concurrently."""
    persona_outputs = {
        "expert": PersonaOutput(**EXPERT_OUTPUT),
        "learner": PersonaOutput(**LEARNER_OUTPUT),
    }

    async def fake_write_persona(persona, fact_pack, handbook_slugs, post_type="business"):
        return persona_outputs[persona], {"tokens_used": 1000, "model_used": "gpt-4o"}

    with patch("services.agents.persona_writer.write_persona", side_effect=fake_write_persona):
        from services.agents.persona_writer import write_all_personas
        results, usage = await write_all_personas(
            fact_pack=SAMPLE_FACT_PACK,
            handbook_slugs=[],
        )

    assert "expert" in results
    assert "learner" in results
    assert "beginner" not in results
    assert "Executive Summary" in results["expert"].en
    assert "무슨 일이 있었나" in results["learner"].ko


@pytest.mark.asyncio
async def test_write_persona_short_content_business_retries():
    """Business post with EN < 3000 chars triggers one retry."""
    short_output = {
        "en": "## Summary\nShort.",
        "ko": "## 요약\n짧음.",
    }
    long_output = EXPERT_OUTPUT

    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = [
        _mock_openai_response(short_output, 200),
        _mock_openai_response(long_output, 2000),
    ]

    with patch("services.agents.persona_writer.get_openai_client", return_value=mock_client), \
         patch("services.agents.persona_writer.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.persona_writer import write_persona
        output, usage = await write_persona(
            persona="expert",
            fact_pack=SAMPLE_FACT_PACK,
            handbook_slugs=[],
            post_type="business",
        )

    assert len(output.en) >= 3000
    assert mock_client.chat.completions.create.call_count == 2


@pytest.mark.asyncio
async def test_write_persona_short_content_research_no_retry():
    """Research post with short EN does NOT retry (length doesn't matter)."""
    short_output = {
        "en": "## Summary\nShort research content.",
        "ko": "## 요약\n짧은 리서치 콘텐츠.",
    }

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(short_output, 200)

    with patch("services.agents.persona_writer.get_openai_client", return_value=mock_client), \
         patch("services.agents.persona_writer.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.persona_writer import write_persona
        output, usage = await write_persona(
            persona="expert",
            fact_pack=SAMPLE_FACT_PACK,
            handbook_slugs=[],
            post_type="research",
        )

    assert output.en == short_output["en"]
    assert mock_client.chat.completions.create.call_count == 1


@pytest.mark.asyncio
async def test_write_persona_json_error_retries():
    """JSON parse failure triggers infra retry."""
    bad_resp = MagicMock()
    bad_resp.choices = [MagicMock()]
    bad_resp.choices[0].message.content = "not json"
    bad_resp.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

    good_resp = _mock_openai_response(EXPERT_OUTPUT)

    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = [bad_resp, good_resp]

    with patch("services.agents.persona_writer.get_openai_client", return_value=mock_client), \
         patch("services.agents.persona_writer.settings") as mock_settings:
        mock_settings.openai_model_main = "gpt-4o"

        from services.agents.persona_writer import write_persona
        output, usage = await write_persona(
            persona="expert",
            fact_pack=SAMPLE_FACT_PACK,
            handbook_slugs=[],
        )

    assert output is not None
    assert mock_client.chat.completions.create.call_count == 2

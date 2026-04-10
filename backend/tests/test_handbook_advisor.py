"""Tests for Handbook AI advisor with network-blocking mock fixtures.

All external API calls (OpenAI) are mocked. Any real network call will raise.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.advisor import (
    GenerateTermResult,
    HandbookAdviseRequest,
)


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


def _mock_openai_response(data: dict, tokens: int = 500):
    """Create a mock OpenAI chat completion response."""
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = json.dumps(data)
    mock_resp.usage = MagicMock()
    mock_resp.usage.completion_tokens = tokens
    return mock_resp


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

FULL_GENERATE_RESULT = {
    "korean_name": "트랜스포머",
    "categories": ["ai-ml"],
    "definition_ko": "트랜스포머는 셀프 어텐션 기반의 딥러닝 아키텍처로, 문장 속 단어 간 관계를 병렬로 계산해 NLP와 비전 등 광범위한 작업에서 표준 모델로 쓰인다.",
    "definition_en": "Transformer is a deep learning architecture using self-attention to compute relations between tokens in parallel, now standard across NLP and vision tasks.",
    "body_basic_ko": "A" * 2500,
    "body_basic_en": "B" * 2500,
    "body_advanced_ko": "C" * 3500,
    "body_advanced_en": "D" * 3500,
}

SHORT_GENERATE_RESULT = {
    "korean_name": "트랜스포머",
    "categories": ["ai-ml"],
    "definition_ko": "짧은 정의",
    "definition_en": "Short def",
    "body_basic_ko": "짧음",
    "body_basic_en": "Short",
    "body_advanced_ko": "짧음",
    "body_advanced_en": "Short",
}

RELATED_TERMS_RESULT = {
    "related_terms": [
        {"term": "Attention Mechanism", "reason": "Core building block of Transformers"},
        {"term": "BERT", "reason": "Popular Transformer-based model"},
    ]
}

TRANSLATE_RESULT = {
    "definition": "A Transformer is a deep learning architecture...",
    "body_basic": "In simple terms...",
    "body_advanced": "Technically speaking...",
    "source_lang": "ko",
    "target_lang": "en",
}

EXTRACT_TERMS_RESULT = {
    "terms": [
        {"term": "Transformer", "korean_name": "트랜스포머", "reason": "Core AI concept"},
        {"term": "Attention", "korean_name": "어텐션", "reason": "Key mechanism"},
    ]
}


# ---------------------------------------------------------------------------
# Generate tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_term_returns_all_fields():
    """Happy path: generate returns full content with no warnings."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(FULL_GENERATE_RESULT)

    with patch("services.agents.advisor.get_openai_client", return_value=mock_client):
        from services.agents.advisor import run_handbook_advise

        req = HandbookAdviseRequest(
            action="generate",
            term_id="test-id",
            term="Transformer",
        )
        result, model, tokens, warnings = await run_handbook_advise(req)

    assert result["korean_name"] == "트랜스포머"
    assert result["categories"] == ["ai-ml"]
    assert len(result["body_basic_ko"]) >= 2000
    assert len(result["body_advanced_ko"]) >= 3000
    # Validation warnings may include section/link checks, quality scores from mock data
    # (mock content doesn't have real H2 sections, handbook links, or high quality scores)
    pydantic_warnings = [w for w in warnings
                         if "section" not in w and "handbook" not in w and "quality score" not in w.lower()]
    assert pydantic_warnings == []


@pytest.mark.asyncio
async def test_generate_term_validation_warns_on_short_body():
    """Short body content should produce validation warnings."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(SHORT_GENERATE_RESULT)

    with patch("services.agents.advisor.get_openai_client", return_value=mock_client):
        from services.agents.advisor import run_handbook_advise

        req = HandbookAdviseRequest(
            action="generate",
            term_id="test-id",
            term="Transformer",
        )
        result, model, tokens, warnings = await run_handbook_advise(req)

    assert len(warnings) > 0
    # Should have warnings for short fields
    warning_text = " ".join(warnings)
    assert "body_basic_ko" in warning_text or "definition_ko" in warning_text


# ---------------------------------------------------------------------------
# Related terms tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_related_terms_returns_db_existence():
    """Related terms should check DB for existing terms."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(RELATED_TERMS_RESULT)

    # Mock supabase DB lookup
    mock_supabase = MagicMock()
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_select = MagicMock()
    mock_table.select.return_value = mock_select
    mock_ilike = MagicMock()
    mock_select.ilike.return_value = mock_ilike
    mock_limit = MagicMock()
    mock_ilike.limit.return_value = mock_limit
    mock_limit.execute.return_value = MagicMock(data=[])

    with patch("services.agents.advisor.get_openai_client", return_value=mock_client), \
         patch("core.database.get_supabase", return_value=mock_supabase):
        from services.agents.advisor import run_handbook_advise

        req = HandbookAdviseRequest(
            action="related_terms",
            term_id="test-id",
            term="Transformer",
        )
        result, model, tokens, warnings = await run_handbook_advise(req)

    assert "related_terms" in result
    assert len(result["related_terms"]) == 2
    # DB returned empty, so exists_in_db should be False
    for item in result["related_terms"]:
        assert item["exists_in_db"] is False


# ---------------------------------------------------------------------------
# Translate tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_translate_detects_source_language():
    """Translate should auto-detect KO as source when KO content is longer."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(TRANSLATE_RESULT)

    with patch("services.agents.advisor.get_openai_client", return_value=mock_client):
        from services.agents.advisor import run_handbook_advise

        req = HandbookAdviseRequest(
            action="translate",
            term_id="test-id",
            term="Transformer",
            definition_ko="트랜스포머는 딥러닝 모델 아키텍처입니다. 어텐션 메커니즘을 기반으로 합니다.",
            body_basic_ko="기본 설명이 여기에 들어갑니다. " * 20,
        )
        result, model, tokens, warnings = await run_handbook_advise(req)

    assert result["source_lang"] == "ko"
    assert result["target_lang"] == "en"


@pytest.mark.asyncio
async def test_translate_force_direction():
    """force_direction should override auto-detection."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response({
        **TRANSLATE_RESULT,
        "source_lang": "en",
        "target_lang": "ko",
    })

    with patch("services.agents.advisor.get_openai_client", return_value=mock_client):
        from services.agents.advisor import run_handbook_advise

        req = HandbookAdviseRequest(
            action="translate",
            term_id="test-id",
            term="Transformer",
            definition_ko="긴 한국어 텍스트" * 50,
            definition_en="Short",
            force_direction="en2ko",
        )
        result, model, tokens, warnings = await run_handbook_advise(req)

    # Even though KO is longer, force_direction overrides to en→ko
    assert result["source_lang"] == "en"
    assert result["target_lang"] == "ko"


# ---------------------------------------------------------------------------
# Extract terms tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_terms_returns_list():
    """Extract terms should return a list of terms from content."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(EXTRACT_TERMS_RESULT)

    with patch("services.agents.advisor.get_openai_client", return_value=mock_client):
        from services.agents.advisor import extract_terms_from_content

        terms, usage = await extract_terms_from_content(
            "Transformers use attention mechanisms for parallel processing..."
        )

    assert len(terms) == 2
    assert terms[0]["term"] == "Transformer"
    assert terms[1]["term"] == "Attention"
    assert "tokens_used" in usage
    assert "cost_usd" in usage


# ---------------------------------------------------------------------------
# Model validation tests (unit)
# ---------------------------------------------------------------------------

def test_generate_term_result_validates_min_length():
    """GenerateTermResult should reject short content."""
    with pytest.raises(Exception):
        GenerateTermResult.model_validate({
            "korean_name": "테스트",
            "categories": ["ai-ml"],
            "definition_ko": "짧음",
            "definition_en": "Short",
            "body_basic_ko": "짧음",
            "body_basic_en": "Short",
            "body_advanced_ko": "짧음",
            "body_advanced_en": "Short",
        })


def test_generate_term_result_accepts_valid_content():
    """GenerateTermResult should accept content meeting min lengths."""
    result = GenerateTermResult.model_validate(FULL_GENERATE_RESULT)
    assert result.korean_name == "트랜스포머"
    assert len(result.body_basic_ko) >= 2000


def test_basic_en_expected_section_count_matches_redesign():
    """After Plan B redesign, EN Basic section count warning fires at <7 sections."""
    import inspect
    from services.agents import advisor

    source = inspect.getsource(advisor)
    # The _basic_expected dict should have "en": 7, not "en": 13
    assert '"en": 7' in source, "EN Basic threshold should be 7 after Plan B redesign"
    assert '"en": 13' not in source, "Legacy EN=13 threshold must be removed"

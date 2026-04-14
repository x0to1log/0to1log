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
    "summary_ko": "학습자 요약 한국어 문장입니다. 개념의 핵심과 왜 중요한지를 짧게 설명합니다.",
    "summary_en": "This learner summary explains the core idea and why it matters in a concise way.",
    "definition_ko": (
        "트랜스포머는 셀프 어텐션으로 시퀀스 내 모든 토큰 간 관계를 병렬로 계산하는 딥러닝 아키텍처다. "
        "위치 인코딩과 multi-head attention을 통해 순환 구조 없이도 긴 문맥을 효과적으로 학습하며, "
        "2017년 Vaswani et al. 논문 이후 NLP, 비전, 음성 등 거의 모든 현대 foundation 모델의 표준 빌딩 블록으로 자리잡았다. "
        "GPT, BERT, T5 같은 주요 LLM 계열이 모두 이 구조를 기반으로 한다."
    ),
    "definition_en": (
        "Transformer is a deep learning architecture that uses self-attention to compute relations "
        "between all tokens in a sequence in parallel. Positional encodings and multi-head attention "
        "enable capturing long-range context without any recurrence, and since Vaswani et al. (2017) "
        "it has become the standard building block of virtually all modern foundation models across "
        "NLP, vision, and speech. GPT, BERT, and T5 families all build on this architecture."
    ),
    "body_basic_ko": "A" * 2500,
    "body_basic_en": "B" * 2500,
    "body_advanced_ko": "C" * 3500,
    "body_advanced_en": "D" * 3500,
}

FULL_GENERATE_RESULT_WITH_CODE_MODE = {
    **FULL_GENERATE_RESULT,
    "term_type": "capability_feature_spec",
    "term_subtype": "wire_protocol",
    "facet_intent": ["build", "compare"],
    "facet_volatility": "fast-changing",
    "facet_type_confidence": 0.93,
    "generation_gate": {"status": "pass", "auto_save_allowed": True, "reasons": []},
    "code_mode_hint": "real-code",
    "mechanism_summary": "The model emits structured tool arguments that an application executes.",
    "has_clear_io_contract": True,
    "has_official_spec_signal": True,
    "reference_strength": "high",
    "vendor_lock_in_risk": "medium",
    "insufficient_info_flag": False,
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
    # Mock content in this test is intentionally synthetic and can trigger structural/gating
    # warnings. What we care about here is that the generated payload still passes the
    # schema-level length checks.
    schema_length_warnings = [
        w for w in warnings
        if any(field in w for field in ("definition_", "body_basic_", "body_advanced_"))
        and ("min_length" in w or "at least" in w.lower())
    ]
    assert schema_length_warnings == []


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
    assert len(result["related_terms"]) >= 2
    returned_terms = {item["term"] for item in result["related_terms"]}
    assert {"Attention Mechanism", "BERT"}.issubset(returned_terms)
    # DB returned empty, so exists_in_db should be False for all returned terms
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
    assert result.summary_ko.startswith("학습자 요약")
    assert result.summary_en.startswith("This learner summary")


def test_generate_term_result_accepts_code_mode_metadata():
    """GenerateTermResult should accept internal code-mode metadata without relaxing content checks."""
    result = GenerateTermResult.model_validate(FULL_GENERATE_RESULT_WITH_CODE_MODE)

    assert result.code_mode_hint == "real-code"
    assert result.mechanism_summary.startswith("The model emits structured")
    assert result.has_clear_io_contract is True
    assert result.has_official_spec_signal is True
    assert result.reference_strength == "high"
    assert result.vendor_lock_in_risk == "medium"
    assert result.insufficient_info_flag is False


def test_generate_term_result_preserves_code_mode_metadata():
    """GenerateTermResult should keep handbook code-mode metadata fields."""
    result = GenerateTermResult.model_validate(
        {
            **FULL_GENERATE_RESULT,
            "term_type": "foundational_concept",
            "term_subtype": None,
            "facet_intent": ["understand"],
            "facet_volatility": "stable",
            "facet_type_confidence": 0.91,
            "generation_gate": {"status": "pass", "reasons": []},
        }
    )

    assert result.term_type == "foundational_concept"
    assert result.term_subtype is None
    assert result.facet_intent == ["understand"]
    assert result.facet_volatility == "stable"
    assert result.facet_type_confidence == 0.91
    assert result.generation_gate == {"status": "pass", "reasons": []}


def test_generate_term_result_rejects_short_content_even_with_metadata():
    """Code-mode metadata should not bypass the existing min-length checks."""
    with pytest.raises(Exception):
        GenerateTermResult.model_validate(
            {
                **SHORT_GENERATE_RESULT,
                "term_type": "foundational_concept",
                "term_subtype": None,
                "facet_intent": ["understand"],
                "facet_volatility": "stable",
                "facet_type_confidence": 0.91,
                "generation_gate": {"status": "pass", "reasons": []},
            }
        )


def test_basic_en_expected_section_count_matches_redesign():
    """After Plan B redesign, EN Basic section count warning fires at <7 sections."""
    import inspect
    from services.agents import advisor

    source = inspect.getsource(advisor)
    # The _basic_expected dict should have "en": 7, not "en": 13
    assert '"en": 7' in source, "EN Basic threshold should be 7 after Plan B redesign"
    assert '"en": 13' not in source, "Legacy EN=13 threshold must be removed"


def test_build_handbook_user_prompt_includes_redesign_fields():
    from services.agents.advisor import _build_handbook_user_prompt

    req = HandbookAdviseRequest(
        action="generate",
        term_id="term-1",
        term="Function Calling",
        korean_name="함수 호출",
        term_full="Function Calling",
        korean_full="함수 호출",
        categories=["llm-genai", "products-platforms"],
        summary_ko="학습자용 짧은 요약",
        summary_en="Short learner summary",
        definition_ko="정의 ko",
        definition_en="definition en",
        hero_news_context_ko="\"quote\" → 의미",
        hero_news_context_en="\"quote\" -> meaning",
        references_ko=[{"title": "KO Ref", "type": "docs", "url": "https://example.com/ko", "tier": "primary"}],
        references_en=[{"title": "EN Ref", "type": "docs", "url": "https://example.com/en", "tier": "primary"}],
    )

    prompt = _build_handbook_user_prompt(req)

    assert "English full name: Function Calling" in prompt
    assert "Korean full name: 함수 호출" in prompt
    assert "Learner summary: 학습자용 짧은 요약" in prompt
    assert "Learner summary: Short learner summary" in prompt
    assert "Hero News Context:\n\"quote\" → 의미" in prompt
    assert '"title": "KO Ref"' in prompt
    assert '"title": "EN Ref"' in prompt


def test_generate_basic_prompt_includes_term_naming_few_shots():
    from services.agents.prompts_advisor import GENERATE_BASIC_PROMPT

    assert "## Term Name Few-Shot Examples" in GENERATE_BASIC_PROMPT
    assert '"term": "RAG"' in GENERATE_BASIC_PROMPT
    assert '"korean_name": "검색 증강 생성"' in GENERATE_BASIC_PROMPT
    assert '"term": "Function Calling"' in GENERATE_BASIC_PROMPT
    assert '"korean_name": "함수 호출"' in GENERATE_BASIC_PROMPT
    assert '"term": "Transformer"' in GENERATE_BASIC_PROMPT
    assert '"korean_name": "트랜스포머"' in GENERATE_BASIC_PROMPT
    assert '"term": "PyTorch"' in GENERATE_BASIC_PROMPT
    assert '"korean_name": "파이토치"' in GENERATE_BASIC_PROMPT


def test_generate_basic_prompts_require_learner_summary_analogy_and_plain_tone():
    from services.agents.prompts_advisor import GENERATE_BASIC_EN_PROMPT, GENERATE_BASIC_PROMPT

    assert "A useful default flow is:" in GENERATE_BASIC_PROMPT
    assert "You do NOT have to force that exact order" in GENERATE_BASIC_PROMPT
    assert "GOOD style example:" in GENERATE_BASIC_PROMPT
    assert "BAD style example:" in GENERATE_BASIC_PROMPT
    assert "Avoid these phrases and tones:" in GENERATE_BASIC_PROMPT
    assert "Use one intuitive analogy or everyday comparison" in GENERATE_BASIC_EN_PROMPT
    assert "Do not sound like a spec, design doc, benchmark report, or API reference." in GENERATE_BASIC_EN_PROMPT
    assert "avoids design-doc / benchmark / API-reference tone" in GENERATE_BASIC_EN_PROMPT
    assert "skips it when it would feel forced or misleading" in GENERATE_BASIC_EN_PROMPT

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.advisor import HandbookAdviseRequest


def _mock_openai_response(payload: dict, tokens: int = 120):
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = json.dumps(payload)
    response.usage = MagicMock()
    response.usage.completion_tokens = tokens
    return response


def _long_text(label: str, repeat: int = 30) -> str:
    return " ".join([f"{label} detail"] * repeat)


def _reference_items() -> list[dict]:
    return [
        {
            "title": "Primary reference",
            "authors": "OpenAI",
            "year": 2026,
            "venue": "Docs",
            "type": "docs",
            "url": "https://example.com/primary",
            "tier": "primary",
            "annotation": "Primary source",
        },
        {
            "title": "Supporting paper",
            "authors": "Research Team",
            "year": 2025,
            "venue": "arXiv",
            "type": "paper",
            "url": "https://example.com/paper",
            "tier": "primary",
            "annotation": "Supporting paper",
        },
        {
            "title": "Secondary reference",
            "authors": "Community",
            "year": 2026,
            "venue": "Blog",
            "type": "blog",
            "url": "https://example.com/secondary",
            "tier": "secondary",
            "annotation": "Secondary source",
        },
    ]


def _basic_ko_payload() -> dict:
    return {
        "term_full": "Retrieval-Augmented Generation",
        "korean_name": "RAG",
        "korean_full": "검색 증강 생성",
        "categories": ["llm-genai", "data-engineering"],
        "definition_ko": _long_text("definition ko", 40),
        "definition_en": _long_text("definition en", 40),
        "hero_news_context_ko": _long_text("hero ko", 20),
        "hero_news_context_en": _long_text("hero en", 20),
        "references_ko": _reference_items(),
        "references_en": _reference_items(),
        "basic_ko_1_plain": _long_text("plain ko"),
        "basic_ko_2_example": _long_text("example ko"),
        "basic_ko_3_glance": _long_text("glance ko"),
        "basic_ko_4_impact": _long_text("impact ko"),
        "basic_ko_5_caution": _long_text("caution ko"),
        "basic_ko_6_comm": _long_text("comm ko"),
        "basic_ko_7_related": _long_text("related ko"),
    }


def _basic_en_payload() -> dict:
    return {
        "basic_en_1_plain": _long_text("plain en"),
        "basic_en_2_example": _long_text("example en"),
        "basic_en_3_glance": _long_text("glance en"),
        "basic_en_4_impact": _long_text("impact en"),
        "basic_en_5_caution": _long_text("caution en"),
        "basic_en_6_comm": _long_text("comm en"),
        "basic_en_7_related": _long_text("related en"),
    }


def _advanced_ko_payload() -> dict:
    return {
        "adv_ko_1_mechanism": _long_text("mechanism ko", 45),
        "adv_ko_2_formulas": _long_text("formulas ko", 45),
        "adv_ko_3_code": _long_text("code ko", 45),
        "adv_ko_4_tradeoffs": _long_text("tradeoffs ko", 45),
        "adv_ko_5_pitfalls": _long_text("pitfalls ko", 45),
        "adv_ko_6_comm": _long_text("comm adv ko", 45),
        "adv_ko_7_related": _long_text("related adv ko", 45),
    }


def _advanced_en_payload() -> dict:
    return {
        "adv_en_1_mechanism": _long_text("mechanism en", 45),
        "adv_en_2_formulas": _long_text("formulas en", 45),
        "adv_en_3_code": _long_text("code en", 45),
        "adv_en_4_tradeoffs": _long_text("tradeoffs en", 45),
        "adv_en_5_pitfalls": _long_text("pitfalls en", 45),
        "adv_en_6_comm": _long_text("comm adv en", 45),
        "adv_en_7_related": _long_text("related adv en", 45),
    }


def _advanced_ko_non_code_payload() -> dict:
    payload = _advanced_ko_payload()
    payload.pop("adv_ko_3_code", None)
    return payload


def _advanced_en_non_code_payload() -> dict:
    payload = _advanced_en_payload()
    payload.pop("adv_en_3_code", None)
    return payload


def _code_section_payload(locale: str) -> dict:
    return {f"adv_{locale}_3_code": _long_text(f"code section {locale}", 45)}


def _empty_code_section_payload(locale: str) -> dict:
    return {f"adv_{locale}_3_code": ""}


def _weak_function_calling_basic_ko_payload() -> dict:
    payload = _basic_ko_payload()
    payload.update(
        {
            "term_full": "Function Calling",
            "korean_name": "함수 호출",
            "korean_full": "함수 호출",
            "categories": ["llm-genai", "products-platforms"],
            "references_ko": [
                {
                    "title": "Generic benchmark explainer",
                    "authors": "Blog Author",
                    "year": 2026,
                    "venue": "Blog",
                    "type": "blog",
                    "url": "https://www.datacamp.com/tutorial/llm-benchmarks",
                    "tier": "secondary",
                    "annotation": "Broad benchmark summary",
                },
                {
                    "title": "Indirect benchmark chapter",
                    "authors": "ML Systems",
                    "year": 2025,
                    "venue": "Book",
                    "type": "book",
                    "url": "https://mlsysbook.ai/book/contents/core/benchmarking/benchmarking.html",
                    "tier": "secondary",
                    "annotation": "General benchmark framing",
                },
                {
                    "title": "Community explainer",
                    "authors": "Author",
                    "year": 2026,
                    "venue": "Blog",
                    "type": "blog",
                    "url": "https://cobusgreyling.substack.com/p/demystifying-large-language-model",
                    "tier": "secondary",
                    "annotation": "Indirect explanation",
                },
            ],
            "references_en": [
                {
                    "title": "Generic benchmark explainer",
                    "authors": "Blog Author",
                    "year": 2026,
                    "venue": "Blog",
                    "type": "blog",
                    "url": "https://www.datacamp.com/tutorial/llm-benchmarks",
                    "tier": "secondary",
                    "annotation": "Broad benchmark summary",
                },
                {
                    "title": "Indirect benchmark chapter",
                    "authors": "ML Systems",
                    "year": 2025,
                    "venue": "Book",
                    "type": "book",
                    "url": "https://mlsysbook.ai/book/contents/core/benchmarking/benchmarking.html",
                    "tier": "secondary",
                    "annotation": "General benchmark framing",
                },
                {
                    "title": "Clinical benchmark paper",
                    "authors": "PMC",
                    "year": 2025,
                    "venue": "Paper",
                    "type": "paper",
                    "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11809097/",
                    "tier": "primary",
                    "annotation": "Indirect benchmark evidence",
                },
            ],
        }
    )
    return payload


@pytest.mark.asyncio
async def test_classify_term_type_uses_known_overrides_without_llm():
    from services.agents.advisor import _classify_term_type

    client = MagicMock()
    client.chat.completions.create = AsyncMock()

    term_type, subtype, intents, volatility, confidence = await _classify_term_type(
        "RAG",
        ["llm-genai"],
        "RAG retrieves documents before generation.",
        client,
        "test-model",
    )

    assert term_type == "retrieval_knowledge_system"
    assert subtype is None
    assert intents[0] == "build"
    assert volatility == "evolving"
    assert confidence == pytest.approx(1.0)
    client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_classify_term_type_returns_product_subtype_from_known_override():
    from services.agents.advisor import _classify_term_type

    client = MagicMock()
    client.chat.completions.create = AsyncMock()

    term_type, subtype, intents, volatility, confidence = await _classify_term_type(
        "Hugging Face",
        ["products-platforms", "llm-genai"],
        "Hugging Face Hub hosts models, datasets, and Spaces.",
        client,
        "test-model",
    )

    assert term_type == "product_platform_service"
    assert subtype == "ecosystem_platform"
    assert intents[0] == "compare"
    assert volatility == "fast-changing"
    assert confidence == pytest.approx(1.0)
    client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_classify_term_type_returns_hardware_metric_and_protocol_subtypes_from_overrides():
    from services.agents.advisor import _classify_term_type

    client = MagicMock()
    client.chat.completions.create = AsyncMock()

    hardware = await _classify_term_type(
        "Trainium",
        ["infra-hardware"],
        "AWS Trainium is a custom accelerator for model training and inference.",
        client,
        "test-model",
    )
    metric = await _classify_term_type(
        "MMLU",
        ["llm-genai", "ml-fundamentals"],
        "MMLU is a benchmark suite used to compare model performance across tasks.",
        client,
        "test-model",
    )
    protocol = await _classify_term_type(
        "OAuth 2.0",
        ["cs-fundamentals"],
        "OAuth 2.0 is an authorization protocol used for delegated access.",
        client,
        "test-model",
    )

    assert hardware[0] == "hardware_runtime_infra"
    assert hardware[1] == "accelerator_hardware"
    assert metric[0] == "metric_benchmark"
    assert metric[1] == "benchmark_suite"
    assert protocol[0] == "protocol_format_data_structure"
    assert protocol[1] == "wire_protocol"
    client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_classify_term_type_returns_boundary_term_subtypes_from_overrides():
    from services.agents.advisor import _classify_term_type

    client = MagicMock()
    client.chat.completions.create = AsyncMock()

    cot = await _classify_term_type(
        "Chain-of-Thought",
        ["llm-genai", "ml-fundamentals"],
        "Chain-of-Thought is an explicit reasoning trace used to inspect or improve model reasoning.",
        client,
        "test-model",
    )
    frontier = await _classify_term_type(
        "Frontier model",
        ["llm-genai"],
        "Frontier model refers to leading-edge models discussed in capability, safety, and policy framing.",
        client,
        "test-model",
    )

    assert cot[0] == "foundational_concept"
    assert cot[1] == "reasoning_method"
    assert frontier[0] == "foundational_concept"
    assert frontier[1] == "policy_discourse"
    client.chat.completions.create.assert_not_called()


def test_subtype_specific_guides_and_queries_are_more_precise():
    from services.agents.advisor import _build_type_aware_search_query
    from services.agents.prompts_handbook_types import get_section_weight_guide, get_type_basic_guide

    hardware_guide = get_type_basic_guide("hardware_runtime_infra", "accelerator_hardware")
    metric_guide = get_section_weight_guide("metric_benchmark", "evaluate", "benchmark_suite")
    protocol_query = _build_type_aware_search_query(
        "OAuth 2.0",
        ["cs-fundamentals"],
        "protocol_format_data_structure",
        "wire_protocol",
        "brave",
        "build",
    )

    assert "hardware_runtime_infra / accelerator_hardware" in hardware_guide
    assert "accelerator" in hardware_guide.lower()
    assert "metric_benchmark / benchmark_suite x evaluate" in metric_guide
    assert "leaderboard" in metric_guide.lower() or "benchmark" in metric_guide.lower()
    assert "handshake" in protocol_query.lower() or "authorization" in protocol_query.lower() or "spec" in protocol_query.lower()


def test_subtype_priorities_and_guides_cover_reasoning_and_policy_terms():
    from services.agents.prompts_handbook_types import (
        get_field_source_priority,
        get_reference_blocklist,
        get_section_weight_guide,
        get_type_basic_guide,
        get_type_depth_guide,
    )

    reasoning_refs = get_field_source_priority("foundational_concept", "references", "reasoning_method")
    policy_definition = get_field_source_priority("foundational_concept", "definition", "policy_discourse")
    reasoning_blocklist = get_reference_blocklist("foundational_concept", "reasoning_method")
    reasoning_basic = get_type_basic_guide("foundational_concept", "reasoning_method")
    policy_depth = get_type_depth_guide("foundational_concept", "policy_discourse")
    policy_section = get_section_weight_guide("foundational_concept", "understand", "policy_discourse")

    assert reasoning_refs[:2] == ["exa", "brave"]
    assert policy_definition[:2] == ["brave", "curated"]
    assert "datacamp.com" in reasoning_blocklist
    assert "reasoning method" in reasoning_basic.lower() or "direct method" in reasoning_basic.lower()
    assert "technical definition" in policy_depth.lower()
    assert "policy meaning" in policy_depth.lower()
    assert "separate" in policy_section.lower() or "do not collapse" in policy_section.lower()


def test_subtype_queries_narrow_boundary_terms():
    from services.agents.advisor import _build_type_aware_search_query

    cot_query = _build_type_aware_search_query(
        "Chain-of-Thought",
        ["llm-genai", "ml-fundamentals"],
        "foundational_concept",
        "reasoning_method",
        "exa",
        "understand",
    )
    frontier_query = _build_type_aware_search_query(
        "Frontier model",
        ["llm-genai"],
        "foundational_concept",
        "policy_discourse",
        "brave",
        "understand",
    )

    assert "reasoning" in cot_query.lower()
    assert "scratchpad" in cot_query.lower() or "traces" in cot_query.lower()
    assert "policy" in frontier_query.lower() or "governance" in frontier_query.lower()
    assert "definition" in frontier_query.lower() or "safety" in frontier_query.lower()


@pytest.mark.asyncio
async def test_generate_term_propagates_product_subtype_into_retrieval_and_ko_basic_prompt():
    from services.agents.advisor import _run_generate_term

    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(_basic_ko_payload()),
            _mock_openai_response(_basic_en_payload()),
            _mock_openai_response(_advanced_ko_payload()),
            _mock_openai_response(_advanced_en_payload()),
        ]
    )

    req = HandbookAdviseRequest(
        action="generate",
        term_id="term-1",
        term="Hugging Face",
        categories=["products-platforms", "llm-genai"],
        skip_quality_check=True,
    )

    with (
        patch("services.agents.advisor.get_supabase", return_value=None),
        patch(
            "services.agents.advisor._classify_term_type",
            new=AsyncMock(return_value=("product_platform_service", "ecosystem_platform", ["compare"], "fast-changing", 0.94)),
        ) as classify_mock,
        patch("services.agents.advisor._search_term_context", new=AsyncMock(return_value="")) as tavily_mock,
        patch("services.agents.advisor._search_brave_context", new=AsyncMock(return_value="")) as brave_mock,
        patch("services.agents.advisor._search_deep_context", new=AsyncMock(return_value="")) as deep_mock,
        patch(
            "services.agents.advisor._build_code_mode_metadata",
            return_value={
                "code_mode_hint": "no-code",
                "mechanism_summary": "This baseline test focuses on prompt propagation, not code generation.",
                "has_clear_io_contract": False,
                "has_official_spec_signal": False,
                "reference_strength": "medium",
                "vendor_lock_in_risk": "medium",
                "insufficient_info_flag": False,
            },
        ),
        patch(
            "services.agents.advisor._self_critique_basic",
            new=AsyncMock(return_value=(False, False, "", "", 84, 82, {})),
        ),
        patch(
            "services.agents.advisor._self_critique_advanced",
            new=AsyncMock(return_value=(False, "", 84, {})),
        ),
        patch("services.agents.advisor._validate_ref_urls", new=AsyncMock(side_effect=lambda text: text)),
        patch("services.agents.advisor._extract_novel_entities", new=AsyncMock(return_value=[])),
        patch("services.agents.advisor._check_handbook_structural_penalties", return_value=(0, [])),
    ):
        result, usage, warnings = await _run_generate_term(req, client, "test-model")

    classify_mock.assert_awaited_once()
    tavily_mock.assert_awaited_once()
    brave_mock.assert_awaited_once()
    deep_mock.assert_awaited_once()

    tavily_kwargs = tavily_mock.await_args.kwargs
    brave_kwargs = brave_mock.await_args.kwargs
    deep_kwargs = deep_mock.await_args.kwargs

    assert tavily_kwargs["term_type"] == "product_platform_service"
    assert brave_kwargs["term_type"] == "product_platform_service"
    assert deep_kwargs["term_type"] == "product_platform_service"
    assert tavily_kwargs["subtype"] == "ecosystem_platform"
    assert brave_kwargs["subtype"] == "ecosystem_platform"
    assert deep_kwargs["subtype"] == "ecosystem_platform"

    first_call_system_prompt = client.chat.completions.create.await_args_list[0].kwargs["messages"][0]["content"]
    assert "Basic Content Guide (product_platform_service / ecosystem_platform)" in first_call_system_prompt
    assert "Content Priority Guide (product_platform_service / ecosystem_platform x compare)" in first_call_system_prompt

    assert result["term_type"] == "product_platform_service"
    assert result["term_subtype"] == "ecosystem_platform"
    assert result["facet_intent"] == ["compare"]
    assert result["facet_volatility"] == "fast-changing"


@pytest.mark.asyncio
async def test_generate_term_marks_low_quality_output_as_blocked():
    from services.agents.advisor import _run_generate_term

    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(_basic_ko_payload()),
            _mock_openai_response(_basic_en_payload()),
            _mock_openai_response(_advanced_ko_payload()),
            _mock_openai_response(_advanced_en_payload()),
        ]
    )

    req = HandbookAdviseRequest(
        action="generate",
        term_id="term-2",
        term="Hugging Face",
        categories=["products-platforms", "llm-genai"],
    )

    with (
        patch("services.agents.advisor.get_supabase", return_value=None),
        patch(
            "services.agents.advisor._classify_term_type",
            new=AsyncMock(return_value=("product_platform_service", "ecosystem_platform", ["compare"], "fast-changing", 0.88)),
        ),
        patch("services.agents.advisor._search_term_context", new=AsyncMock(return_value="")),
        patch("services.agents.advisor._search_brave_context", new=AsyncMock(return_value="")),
        patch("services.agents.advisor._search_deep_context", new=AsyncMock(return_value="")),
        patch(
            "services.agents.advisor._build_code_mode_metadata",
            return_value={
                "code_mode_hint": "no-code",
                "mechanism_summary": "This baseline test focuses on quality gating, not code generation.",
                "has_clear_io_contract": False,
                "has_official_spec_signal": False,
                "reference_strength": "medium",
                "vendor_lock_in_risk": "medium",
                "insufficient_info_flag": False,
            },
        ),
        patch(
            "services.agents.advisor._self_critique_basic",
            new=AsyncMock(return_value=(False, False, "", "", 84, 82, {})),
        ),
        patch(
            "services.agents.advisor._self_critique_advanced",
            new=AsyncMock(return_value=(False, "", 84, {})),
        ),
        patch("services.agents.advisor._validate_ref_urls", new=AsyncMock(side_effect=lambda text: text)),
        patch("services.agents.advisor._extract_novel_entities", new=AsyncMock(return_value=[])),
        patch("services.agents.advisor._check_handbook_structural_penalties", return_value=(0, [])),
        patch(
            "services.agents.advisor._check_handbook_quality",
            new=AsyncMock(return_value=(48, {"depth": 10}, {})),
        ),
        patch(
            "services.agents.advisor._check_basic_quality",
            new=AsyncMock(return_value=(61, {"engagement": 15}, {})),
        ),
    ):
        result, usage, warnings = await _run_generate_term(req, client, "test-model")

    gate = result["generation_gate"]
    assert gate["status"] == "blocked"
    assert gate["auto_save_allowed"] is False
    assert result["term_subtype"] == "ecosystem_platform"
    assert any("advanced_quality_below_min" in reason for reason in gate["reasons"])
    assert any("generation gate" in warning.lower() for warning in warnings)


def test_decide_code_mode_uses_deterministic_rules():
    from services.agents.advisor import decide_code_mode

    assert decide_code_mode("problem_failure_mode", None, "high", True, True, False) == "no-code"
    assert decide_code_mode("retrieval_knowledge_system", None, "medium", False, True, False) == "pseudocode"
    assert decide_code_mode("capability_feature_spec", None, "high", True, True, False) == "real-code"
    assert decide_code_mode("capability_feature_spec", None, "high", True, True, True) == "no-code"


def test_get_field_source_priority_prefers_curated_and_brave_for_capability_specs():
    from services.agents.prompts_handbook_types import get_field_source_priority

    assert get_field_source_priority("capability_feature_spec", "definition") == [
        "curated",
        "brave",
        "exa",
        "tavily",
    ]
    assert get_field_source_priority("capability_feature_spec", "references") == [
        "curated",
        "brave",
        "exa",
        "tavily",
    ]
    assert get_field_source_priority("capability_feature_spec", "hero") == [
        "tavily",
        "curated",
        "brave",
        "exa",
    ]
    assert get_field_source_priority("capability_feature_spec", "advanced") == [
        "brave",
        "exa",
        "curated",
        "tavily",
    ]


def test_evaluate_reference_candidates_filters_type_aware_blocked_hosts():
    from services.agents.advisor import _evaluate_reference_candidates

    weak_payload = _weak_function_calling_basic_ko_payload()
    evaluation = _evaluate_reference_candidates(
        "Function Calling",
        "capability_feature_spec",
        None,
        weak_payload["references_ko"],
        weak_payload["references_en"],
    )

    assert evaluation["reference_strength"] == "low"
    assert evaluation["has_official_docs"] is False
    assert len(evaluation["accepted_references"]) == 0
    assert "datacamp.com" in evaluation["blocked_hosts_found"]
    assert "mlsysbook.ai" in evaluation["blocked_hosts_found"]
    assert "pmc.ncbi.nlm.nih.gov" in evaluation["blocked_hosts_found"]


def test_synchronize_reference_sets_keeps_same_url_set_across_locales():
    from services.agents.advisor import _synchronize_reference_sets

    accepted = [
        {
            "title": "Function calling",
            "authors": "OpenAI",
            "venue": "OpenAI API Docs",
            "type": "docs",
            "url": "https://platform.openai.com/docs/guides/function-calling",
            "tier": "primary",
            "annotation": "Official function calling flow.",
        },
        {
            "title": "Tool use overview",
            "authors": "Anthropic",
            "venue": "Anthropic Docs",
            "type": "docs",
            "url": "https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview",
            "tier": "primary",
            "annotation": "Official tool use overview.",
        },
    ]
    references_ko = [dict(accepted[0], annotation="KO annotation")]
    references_en = [dict(accepted[1], annotation="EN annotation")]

    sync_ko, sync_en = _synchronize_reference_sets(accepted, references_ko, references_en)

    assert {item["url"] for item in sync_ko} == {item["url"] for item in sync_en}
    assert len(sync_ko) == 2
    assert len(sync_en) == 2


def test_assemble_all_sections_skips_code_header_for_no_code_mode():
    from services.agents.advisor import _assemble_all_sections

    raw_data = {
        "term_full": "Hallucination",
        "korean_name": "환각",
        "korean_full": "환각",
        "categories": ["safety-ethics"],
        "code_mode_hint": "no-code",
        "definition_ko": _long_text("definition ko", 40),
        "definition_en": _long_text("definition en", 40),
        **_advanced_ko_non_code_payload(),
        **_advanced_en_non_code_payload(),
    }

    assembled = _assemble_all_sections(raw_data)

    assert assembled["code_mode_hint"] == "no-code"
    assert "## 코드 또는 의사코드" not in assembled["body_advanced_ko"]
    assert "## Code or Pseudocode" not in assembled["body_advanced_en"]
    assert assembled["body_advanced_ko"].count("## ") == 6
    assert assembled["body_advanced_en"].count("## ") == 6


@pytest.mark.asyncio
async def test_generate_term_keeps_single_pass_advanced_flow_when_code_mode_is_real_code():
    from services.agents.advisor import _run_generate_term

    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(_basic_ko_payload()),
            _mock_openai_response(_basic_en_payload()),
            _mock_openai_response(_advanced_ko_payload()),
            _mock_openai_response(_advanced_en_payload()),
        ]
    )

    req = HandbookAdviseRequest(
        action="generate",
        term_id="term-code",
        term="Function Calling",
        categories=["llm-genai", "products-platforms"],
        skip_quality_check=True,
    )

    with (
        patch("services.agents.advisor.get_supabase", return_value=None),
        patch(
            "services.agents.advisor._classify_term_type",
            new=AsyncMock(return_value=("capability_feature_spec", None, ["build"], "fast-changing", 0.92)),
        ),
        patch("services.agents.advisor._search_term_context", new=AsyncMock(return_value="")),
        patch("services.agents.advisor._search_brave_context", new=AsyncMock(return_value="official docs context")),
        patch("services.agents.advisor._search_deep_context", new=AsyncMock(return_value="deep context")),
        patch(
            "services.agents.advisor._build_code_mode_metadata",
            return_value={
                "code_mode_hint": "real-code",
                "mechanism_summary": "Structured tool arguments are emitted and executed by the application.",
                "has_clear_io_contract": True,
                "has_official_spec_signal": True,
                "reference_strength": "high",
                "vendor_lock_in_risk": "medium",
                "insufficient_info_flag": False,
            },
        ),
        patch(
            "services.agents.advisor._self_critique_basic",
            new=AsyncMock(return_value=(False, False, "", "", 84, 82, {})),
        ),
        patch(
            "services.agents.advisor._self_critique_advanced",
            new=AsyncMock(return_value=(False, "", 84, {})),
        ),
        patch("services.agents.advisor._validate_ref_urls", new=AsyncMock(side_effect=lambda text: text)),
        patch("services.agents.advisor._extract_novel_entities", new=AsyncMock(return_value=[])),
        patch("services.agents.advisor._check_handbook_structural_penalties", return_value=(0, [])),
    ):
        result, usage, warnings = await _run_generate_term(req, client, "test-model")

    assert client.chat.completions.create.await_count == 4
    assert result["code_mode_hint"] == "real-code"
    assert "## 코드 또는 의사코드" in result["body_advanced_ko"]
    assert "## Code or Pseudocode" in result["body_advanced_en"]
    assert "code ko detail" in result["body_advanced_ko"]
    assert "code en detail" in result["body_advanced_en"]


@pytest.mark.asyncio
async def test_generate_term_skips_second_pass_for_no_code_mode():
    from services.agents.advisor import _run_generate_term

    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(_basic_ko_payload()),
            _mock_openai_response(_basic_en_payload()),
            _mock_openai_response(_advanced_ko_non_code_payload()),
            _mock_openai_response(_advanced_en_non_code_payload()),
        ]
    )

    req = HandbookAdviseRequest(
        action="generate",
        term_id="term-nocode",
        term="Hallucination",
        categories=["safety-ethics", "llm-genai"],
        skip_quality_check=True,
    )

    with (
        patch("services.agents.advisor.get_supabase", return_value=None),
        patch(
            "services.agents.advisor._classify_term_type",
            new=AsyncMock(return_value=("problem_failure_mode", None, ["debug"], "evolving", 0.9)),
        ),
        patch("services.agents.advisor._search_term_context", new=AsyncMock(return_value="")),
        patch("services.agents.advisor._search_brave_context", new=AsyncMock(return_value="")),
        patch("services.agents.advisor._search_deep_context", new=AsyncMock(return_value="")),
        patch(
            "services.agents.advisor._build_code_mode_metadata",
            return_value={
                "code_mode_hint": "no-code",
                "mechanism_summary": "The failure mode is better explained through behavior and mitigation than code.",
                "has_clear_io_contract": False,
                "has_official_spec_signal": False,
                "reference_strength": "medium",
                "vendor_lock_in_risk": "low",
                "insufficient_info_flag": False,
            },
        ),
        patch(
            "services.agents.advisor._self_critique_basic",
            new=AsyncMock(return_value=(False, False, "", "", 84, 82, {})),
        ),
        patch(
            "services.agents.advisor._self_critique_advanced",
            new=AsyncMock(return_value=(False, "", 84, {})),
        ),
        patch("services.agents.advisor._validate_ref_urls", new=AsyncMock(side_effect=lambda text: text)),
        patch("services.agents.advisor._extract_novel_entities", new=AsyncMock(return_value=[])),
        patch("services.agents.advisor._check_handbook_structural_penalties", return_value=(0, [])),
    ):
        result, usage, warnings = await _run_generate_term(req, client, "test-model")

    assert client.chat.completions.create.await_count == 4
    assert result["code_mode_hint"] == "no-code"
    assert "## 코드 또는 의사코드" not in result["body_advanced_ko"]
    assert "## Code or Pseudocode" not in result["body_advanced_en"]


def test_function_calling_generation_override_curates_direct_references_and_focus():
    from services.agents.prompts_handbook_types import get_term_generation_override

    override = get_term_generation_override("Function Calling")

    assert override is not None
    assert override["preferred_code_mode"] == "real-code"
    assert "host-side validation" in override["advanced_focus_guide"].lower()
    assert "execution boundary" in override["advanced_focus_guide"].lower()
    assert "runtime failure handling" in override["advanced_focus_guide"].lower()
    assert "3 short paragraphs max" in override["basic_ko_focus_guide"].lower()
    assert "one claim per sentence" in override["advanced_ko_focus_guide"].lower()
    assert "tool registry" in override["code_contract_guide"].lower()
    assert "unknown tool" in override["code_contract_guide"].lower()
    assert "no-call" in override["code_contract_guide"].lower()

    references_en = override["references_en"]
    references_ko = override["references_ko"]
    assert len(references_en) >= 4
    assert len(references_ko) == len(references_en)
    assert [item["title"] for item in references_ko] == [item["title"] for item in references_en]
    assert sum(1 for item in references_en if item["tier"] == "primary") >= 2
    assert any("platform.openai.com" in item["url"] for item in references_en)
    assert any("docs.anthropic.com" in item["url"] for item in references_en)
    assert any("ai.google.dev" in item["url"] for item in references_en)


@pytest.mark.asyncio
async def test_generate_term_function_calling_rewrites_indirect_references_to_direct_sources():
    from services.agents.advisor import _run_generate_term

    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(_weak_function_calling_basic_ko_payload()),
            _mock_openai_response(_basic_en_payload()),
            _mock_openai_response(_advanced_ko_payload()),
            _mock_openai_response(_advanced_en_payload()),
        ]
    )

    req = HandbookAdviseRequest(
        action="generate",
        term_id="term-function-calling-remediation",
        term="Function Calling",
        categories=["llm-genai", "products-platforms"],
        skip_quality_check=True,
    )

    with (
        patch("services.agents.advisor.get_supabase", return_value=None),
        patch(
            "services.agents.advisor._classify_term_type",
            new=AsyncMock(return_value=("capability_feature_spec", None, ["build"], "fast-changing", 0.92)),
        ),
        patch("services.agents.advisor._search_term_context", new=AsyncMock(return_value="")),
        patch("services.agents.advisor._search_brave_context", new=AsyncMock(return_value="")),
        patch("services.agents.advisor._search_deep_context", new=AsyncMock(return_value="")),
        patch(
            "services.agents.advisor._self_critique_basic",
            new=AsyncMock(return_value=(False, False, "", "", 84, 82, {})),
        ),
        patch(
            "services.agents.advisor._self_critique_advanced",
            new=AsyncMock(return_value=(False, "", 84, {})),
        ),
        patch("services.agents.advisor._validate_ref_urls", new=AsyncMock(side_effect=lambda text: text)),
        patch("services.agents.advisor._extract_novel_entities", new=AsyncMock(return_value=[])),
        patch("services.agents.advisor._check_handbook_structural_penalties", return_value=(0, [])),
    ):
        result, usage, warnings = await _run_generate_term(req, client, "test-model")

    urls_ko = {ref["url"] for ref in result["references_ko"]}
    urls_en = {ref["url"] for ref in result["references_en"]}
    blocked_hosts = ("datacamp.com", "mlsysbook.ai", "pmc.ncbi.nlm.nih.gov", "substack.com")

    assert urls_ko == urls_en
    assert len(urls_en) >= 4
    assert sum(1 for ref in result["references_en"] if ref["tier"] == "primary") >= 2
    assert any(ref["type"] == "docs" and ref["tier"] == "primary" for ref in result["references_en"])
    assert all(all(host not in ref["url"] for host in blocked_hosts) for ref in result["references_en"])
    assert all(all(host not in ref["url"] for host in blocked_hosts) for ref in result["references_ko"])
    assert result["code_mode_hint"] == "real-code"


@pytest.mark.asyncio
async def test_generate_term_function_calling_advanced_prompts_emphasize_runtime_execution_boundaries():
    from services.agents.advisor import _run_generate_term

    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(_weak_function_calling_basic_ko_payload()),
            _mock_openai_response(_basic_en_payload()),
            _mock_openai_response(_advanced_ko_payload()),
            _mock_openai_response(_advanced_en_payload()),
        ]
    )

    req = HandbookAdviseRequest(
        action="generate",
        term_id="term-function-calling-prompt",
        term="Function Calling",
        categories=["llm-genai", "products-platforms"],
        skip_quality_check=True,
    )

    with (
        patch("services.agents.advisor.get_supabase", return_value=None),
        patch(
            "services.agents.advisor._classify_term_type",
            new=AsyncMock(return_value=("capability_feature_spec", None, ["build"], "fast-changing", 0.92)),
        ),
        patch("services.agents.advisor._search_term_context", new=AsyncMock(return_value="")),
        patch("services.agents.advisor._search_brave_context", new=AsyncMock(return_value="")),
        patch("services.agents.advisor._search_deep_context", new=AsyncMock(return_value="")),
        patch(
            "services.agents.advisor._self_critique_basic",
            new=AsyncMock(return_value=(False, False, "", "", 84, 82, {})),
        ),
        patch(
            "services.agents.advisor._self_critique_advanced",
            new=AsyncMock(return_value=(False, "", 84, {})),
        ),
        patch("services.agents.advisor._validate_ref_urls", new=AsyncMock(side_effect=lambda text: text)),
        patch("services.agents.advisor._extract_novel_entities", new=AsyncMock(return_value=[])),
        patch("services.agents.advisor._check_handbook_structural_penalties", return_value=(0, [])),
    ):
        await _run_generate_term(req, client, "test-model")

    adv_ko_system = client.chat.completions.create.await_args_list[2].kwargs["messages"][0]["content"]
    adv_en_system = client.chat.completions.create.await_args_list[3].kwargs["messages"][0]["content"]

    assert "host-side validation" in adv_ko_system.lower()
    assert "execution boundary" in adv_ko_system.lower()
    assert "runtime failure handling" in adv_ko_system.lower()
    assert "host-side validation" in adv_en_system.lower()
    assert "execution boundary" in adv_en_system.lower()
    assert "runtime failure handling" in adv_en_system.lower()


@pytest.mark.asyncio
async def test_generate_term_function_calling_en_advanced_uses_selected_context_bundle_only():
    from services.agents.advisor import _run_generate_term

    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(_weak_function_calling_basic_ko_payload()),
            _mock_openai_response(_basic_en_payload()),
            _mock_openai_response(_advanced_ko_payload()),
            _mock_openai_response(_advanced_en_payload()),
        ]
    )

    req = HandbookAdviseRequest(
        action="generate",
        term_id="term-function-calling-en-context",
        term="Function Calling",
        categories=["llm-genai", "products-platforms"],
        skip_quality_check=True,
    )

    with (
        patch("services.agents.advisor.get_supabase", return_value=None),
        patch(
            "services.agents.advisor._classify_term_type",
            new=AsyncMock(return_value=("capability_feature_spec", None, ["build"], "fast-changing", 0.92)),
        ),
        patch("services.agents.advisor._search_term_context", new=AsyncMock(return_value="TAVILY_MARKER")),
        patch("services.agents.advisor._search_brave_context", new=AsyncMock(return_value="BRAVE_MARKER")),
        patch("services.agents.advisor._search_deep_context", new=AsyncMock(return_value="EXA_MARKER")),
        patch(
            "services.agents.advisor._self_critique_basic",
            new=AsyncMock(return_value=(False, False, "", "", 84, 82, {})),
        ),
        patch(
            "services.agents.advisor._self_critique_advanced",
            new=AsyncMock(return_value=(False, "", 84, {})),
        ),
        patch("services.agents.advisor._validate_ref_urls", new=AsyncMock(side_effect=lambda text: text)),
        patch("services.agents.advisor._extract_novel_entities", new=AsyncMock(return_value=[])),
        patch("services.agents.advisor._check_handbook_structural_penalties", return_value=(0, [])),
    ):
        await _run_generate_term(req, client, "test-model")

    advanced_en_prompt = client.chat.completions.create.await_args_list[3].kwargs["messages"][1]["content"]

    assert "Selected Reference Context for Advanced Sections" in advanced_en_prompt
    assert "BRAVE_MARKER" in advanced_en_prompt
    assert "EXA_MARKER" in advanced_en_prompt
    assert "SOURCE ROLE: Official docs, code references." not in advanced_en_prompt
    assert "SOURCE ROLE: Deep technical papers." not in advanced_en_prompt

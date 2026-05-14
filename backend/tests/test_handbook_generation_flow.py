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
    payload["adv_ko_3_code"] = _long_text("operational procedure ko", 45)
    return payload


def _advanced_en_non_code_payload() -> dict:
    payload = _advanced_en_payload()
    payload["adv_en_3_code"] = _long_text("operational procedure en", 45)
    return payload


def _code_section_payload(locale: str) -> dict:
    return {f"adv_{locale}_3_code": _long_text(f"code section {locale}", 45)}


def _empty_code_section_payload(locale: str) -> dict:
    return {f"adv_{locale}_3_code": ""}


def test_schema_dollar_identifiers_are_sanitized_outside_code_fences():
    from services.agents.advisor import _sanitize_schema_dollar_identifiers

    text = (
        "Normalize $ref/$defs and $schema before markdown rendering.\n\n"
        "```python\n"
        "schema = {'$schema': 'https://json-schema.org/draft/2020-12/schema'}\n"
        "```\n"
    )

    out = _sanitize_schema_dollar_identifiers(text)

    assert "`$ref`/`$defs`" in out
    assert "`$schema`" in out
    assert "'$schema':" in out


def test_python_code_fence_validator_flags_invalid_python_snippets():
    from services.agents.advisor import _validate_python_code_fences

    warnings = _validate_python_code_fences(
        "```python\n"
        "resp = client.responses.create(text={'format': {'type': 'json_object'}}, ...)\n"
        "```"
    )

    assert warnings
    assert "invalid Python code fence" in warnings[0]


def test_mixed_script_artifact_detector_flags_chinese_character_inside_korean_text():
    from services.agents.advisor import _detect_mixed_script_artifacts

    warnings = _detect_mixed_script_artifacts("행동 배치의 실행语의미를 설명한다.")

    assert warnings
    assert "mixed-script artifact" in warnings[0]


def test_assemble_all_sections_omits_specs_for_capability_feature_terms():
    from services.agents.advisor import _assemble_all_sections

    raw = {
        "term_type": "capability_feature_spec",
        "code_mode_hint": "real-code",
        "adv_en_1_mechanism": _long_text("mechanism en"),
        "adv_en_specs": {
            "parameters": "not_published",
            "context_window": "not_published",
            "training_data": "not_published",
            "compute_cost": "not_published",
            "latency_throughput": "not_published",
            "benchmarks": [],
        },
        "adv_en_2_formulas": _long_text("architecture en"),
        "adv_en_3_code": "```python\nprint('ok')\n```",
        "adv_en_4_tradeoffs": _long_text("tradeoffs en"),
        "adv_en_5_pitfalls": _long_text("pitfalls en"),
        "adv_en_6_comm": _long_text("comm en"),
        "adv_en_7_related": _long_text("related en"),
    }

    data = _assemble_all_sections(raw)

    assert "Key Specifications" not in data["body_advanced_en"]
    assert "not_published" not in data["body_advanced_en"]


def test_model_algorithm_policy_does_not_request_numeric_specs_by_default():
    from services.agents.prompts_handbook_types import build_artifact_policy_block

    block = build_artifact_policy_block(
        "model_algorithm_family",
        None,
        "deep-learning",
        "pseudocode",
    )

    assert "Specs mode: off" in block
    assert "Do NOT output adv_ko_specs or adv_en_specs" in block


def test_company_actor_policy_does_not_request_numeric_specs():
    from services.agents.prompts_handbook_types import build_artifact_policy_block

    block = build_artifact_policy_block(
        "product_platform_service",
        "ai_company_ecosystem_actor",
        "products-platforms",
        "no-code",
    )

    assert "Specs mode: off" in block
    assert "Do NOT output adv_ko_specs or adv_en_specs" in block


def test_assemble_all_sections_omits_all_not_published_specs_for_generic_terms():
    from services.agents.advisor import _assemble_all_sections

    raw = {
        "term_type": "hardware_runtime_infra",
        "code_mode_hint": "pseudocode",
        "adv_en_1_mechanism": _long_text("mechanism en"),
        "adv_en_specs": {
            "parameters": "not_published",
            "context_window": "not_published",
            "training_data": "not_published",
            "compute_cost": "not_published",
            "latency_throughput": "not_published",
            "benchmarks": [],
        },
        "adv_en_2_formulas": _long_text("architecture en"),
        "adv_en_3_code": "```python\nprint('ok')\n```",
        "adv_en_4_tradeoffs": _long_text("tradeoffs en"),
        "adv_en_5_pitfalls": _long_text("pitfalls en"),
        "adv_en_6_comm": _long_text("comm en"),
        "adv_en_7_related": _long_text("related en"),
    }

    data = _assemble_all_sections(raw)

    assert "Key Specifications" not in data["body_advanced_en"]
    assert "not_published" not in data["body_advanced_en"]
    assert "none reported in original paper" not in data["body_advanced_en"]


def test_assemble_all_sections_keeps_concrete_specs_for_hardware_terms():
    from services.agents.advisor import _assemble_all_sections

    raw = {
        "term_type": "hardware_runtime_infra",
        "code_mode_hint": "pseudocode",
        "adv_en_1_mechanism": _long_text("mechanism en"),
        "adv_en_specs": {
            "parameters": "",
            "context_window": "",
            "training_data": "",
            "compute_cost": "",
            "latency_throughput": "HBM3 memory bandwidth is published by the vendor.",
            "benchmarks": [],
        },
        "adv_en_2_formulas": _long_text("architecture en"),
        "adv_en_3_code": "```python\nprint('ok')\n```",
        "adv_en_4_tradeoffs": _long_text("tradeoffs en"),
        "adv_en_5_pitfalls": _long_text("pitfalls en"),
        "adv_en_6_comm": _long_text("comm en"),
        "adv_en_7_related": _long_text("related en"),
    }

    data = _assemble_all_sections(raw)

    assert "Key Hardware and Runtime Specs" in data["body_advanced_en"]
    assert "HBM3 memory bandwidth" in data["body_advanced_en"]
    assert "not_published" not in data["body_advanced_en"]
    assert "none reported in original paper" not in data["body_advanced_en"]


def test_optional_specs_terms_allow_advanced_without_specs_section():
    from services.agents.advisor import (
        ADVANCED_SECTIONS_EN,
        ADVANCED_SECTIONS_KO,
        BASIC_SECTIONS_EN,
        BASIC_SECTIONS_KO,
        _assemble_all_sections,
        _build_handbook_remediation_issues,
    )

    raw = {
        "term": "GPU",
        "term_full": "GPU",
        "korean_name": "그래픽 처리 장치",
        "korean_full": "그래픽 처리 장치",
        "term_type": "hardware_runtime_infra",
        "code_mode_hint": "pseudocode",
        "definition_ko": "GPU는 병렬 계산 가속기다.",
        "definition_en": "A GPU is a parallel compute accelerator.",
        "hero_news_context_ko": "one\ntwo\nthree",
        "hero_news_context_en": "one\ntwo\nthree",
        "references_ko": [{"tier": "primary"}, {"tier": "primary"}, {"tier": "secondary"}],
        "references_en": [{"tier": "primary"}, {"tier": "primary"}, {"tier": "secondary"}],
        **{key: _long_text(key, 30) for key, _ in BASIC_SECTIONS_KO},
        **{key: _long_text(key, 30) for key, _ in BASIC_SECTIONS_EN},
        **{key: _long_text(key, 30) for key, _ in ADVANCED_SECTIONS_KO},
        **{key: _long_text(key, 30) for key, _ in ADVANCED_SECTIONS_EN},
    }
    assembled = _assemble_all_sections(raw)

    assert assembled["body_advanced_ko"].count("## ") == 7
    assert assembled["body_advanced_en"].count("## ") == 7

    issues = _build_handbook_remediation_issues(assembled, [])
    issue_codes = {issue["code"] for issue in issues}

    assert "advanced_sections_incomplete" not in issue_codes
    assert "advanced_heading_shape_invalid" not in issue_codes


def test_capability_depth_guide_discourages_provider_inventory_and_long_code():
    from services.agents.prompts_handbook_types import get_type_depth_guide

    guide = get_type_depth_guide("capability_feature_spec")

    assert "host/runtime boundary" in guide
    assert "provider documentation inventory" in guide
    assert "concise code capsule" in guide
    assert "code capsule" in guide


def test_foundational_llm_guides_prefer_practical_system_depth_over_academic_formalism():
    from services.agents.prompts_handbook_types import (
        build_artifact_policy_block,
        build_category_block,
        get_type_depth_guide,
    )

    guide = get_type_depth_guide("foundational_concept")
    category = build_category_block("llm-genai")
    artifact = build_artifact_policy_block(
        "foundational_concept",
        None,
        "llm-genai",
        "pseudocode",
    )
    combined = f"{guide}\n{category}\n{artifact}"

    assert "design review" in combined
    assert "runtime boundaries" in combined
    assert "component responsibilities" in combined
    assert "Do not lead with research formalism" in combined
    assert "model-only explanation" in combined
    assert "host/runtime/orchestrator" in combined
    assert "failure-path" in combined
    assert "POMDP" in combined


def test_capability_and_workflow_guides_keep_advanced_glossary_scoped():
    from services.agents.prompts_handbook_types import get_type_depth_guide

    capability = get_type_depth_guide("capability_feature_spec")
    workflow = get_type_depth_guide("system_workflow_pattern")
    combined = f"{capability}\n{workflow}"

    assert "glossary deep-dive" in combined
    assert "implementation runbook" in combined
    assert "adjacent term boundaries" in combined
    assert "provider-specific" in combined


def test_advanced_code_prompt_prioritizes_teaching_artifact_quality_over_shortness():
    from services.agents.prompts_advisor import GENERATE_ADVANCED_EN_PROMPT, GENERATE_ADVANCED_PROMPT

    combined = f"{GENERATE_ADVANCED_PROMPT}\n{GENERATE_ADVANCED_EN_PROMPT}"

    assert "teaching artifact" in combined
    assert "not necessarily the shortest code" in combined
    assert "Every line should earn its place" in combined
    assert "core mechanism" in combined
    assert "It may be longer when those lines explain the concept" in combined
    assert "code capsule" in combined
    assert "one fenced code block" in combined
    assert "input/schema definition" in combined
    assert "host-side execution boundary" in combined
    assert "Do not include:" in combined
    assert "environment setup" in combined
    assert "full retry framework" in combined
    assert "Real production-grade code" not in combined
    assert "15+ substantial lines" not in combined


def test_advanced_prompt_restricts_high_risk_claims_to_final_references():
    from services.agents.prompts_advisor import GENERATE_ADVANCED_EN_PROMPT, GENERATE_ADVANCED_PROMPT

    combined = f"{GENERATE_ADVANCED_PROMPT}\n{GENERATE_ADVANCED_EN_PROMPT}"

    assert "named products, model versions, benchmark numbers, paper names, or metrics" in combined
    assert "appear in the final references" in combined
    assert "If the reference set does not support a detail, omit it" in combined


def test_advanced_prompt_frames_depth_as_glossary_deep_dive_not_runbook():
    from services.agents.prompts_advisor import GENERATE_ADVANCED_EN_PROMPT, GENERATE_ADVANCED_PROMPT

    combined = f"{GENERATE_ADVANCED_PROMPT}\n{GENERATE_ADVANCED_EN_PROMPT}"

    assert "glossary deep-dive" in combined
    assert "not an implementation runbook" in combined
    assert "concept boundary" in combined
    assert "responsibility split" in combined
    assert "decision criteria" in combined
    assert "provider-specific fields" in combined
    assert "billing metadata" in combined
    assert "compact contract example" in combined
    assert "adjacent terms" in combined


def test_unsupported_reference_claim_guard_flags_entities_and_metrics_missing_from_refs():
    from services.agents.advisor import _detect_unsupported_reference_claims

    data = {
        "body_advanced_en": (
            "NVIDIA defines ISL and OSL this way. "
            "Kimi-K2-Thinking hides old tool outputs. "
            "A document LVLM benchmark reports F1 44.9%. "
            "Sonnet 4.6 supports this workflow."
        ),
        "references_en": [
            {
                "title": "Context windows",
                "authors": "Anthropic",
                "venue": "Anthropic Docs",
                "url": "https://platform.claude.com/docs/en/build-with-claude/context-windows",
            },
            {
                "title": "Long context",
                "authors": "Google",
                "venue": "Google Cloud Docs",
                "url": "https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/long-context",
            },
        ],
        "references_ko": [],
    }

    warnings = _detect_unsupported_reference_claims(data)

    assert any("NVIDIA" in warning for warning in warnings)
    assert any("Kimi-K2-Thinking" in warning for warning in warnings)
    assert any("F1 44.9%" in warning for warning in warnings)
    assert any("Sonnet 4.6" in warning for warning in warnings)


def test_remediation_issues_classify_claims_related_tags_and_code_mismatch():
    from services.agents.advisor import _build_handbook_remediation_issues

    data = {
        "term_type": "capability_feature_spec",
        "code_mode_hint": "pseudocode",
        "definition_en": " ".join(["This definition is intentionally too long"] * 90),
        "body_advanced_ko": (
            "## 기술 정의와 동작 원리\n"
            "핵심 동작을 설명한다.\n\n"
            "## 수식·아키텍처·도표\n"
            "구조를 설명한다.\n\n"
            "## 코드 또는 의사코드\n"
            "```python\n"
            "def preflight_budget():\n"
            "    pass\n"
            "```\n\n"
            "## 프로덕션 함정\n"
            "주의점을 설명한다.\n\n"
            "## 트레이드오프\n"
            "판단 기준을 설명한다.\n\n"
            "## 업계 대화\n"
            "대화 예시를 설명한다.\n\n"
            "## 선행·대안·확장 개념\n"
            "- (prerequisite) **Tokenization** - needed first"
        ),
        "body_advanced_en": (
            "## Technical Definition & How It Works\n"
            "NVIDIA defines the term this way.\n\n"
            "## Formulas, Architecture, and Diagrams\n"
            "Architecture notes.\n\n"
            "## Code or Pseudocode\n"
            "```python\n"
            "def preflight_budget():\n"
            "    pass\n\n"
            "def reserve_output_tokens():\n"
            "    pass\n\n"
            "def compact_history():\n"
            "    pass\n\n"
            "def fail_fast():\n"
            "    pass\n"
            "```\n\n"
            "## Production Pitfalls\n"
            "Pitfalls.\n\n"
            "## Tradeoffs - When to Use What\n"
            "Tradeoffs.\n\n"
            "## Industry Communication\n"
            "Communication.\n\n"
            "## Prerequisites, Alternatives, and Extensions\n"
            "- (prerequisite) **Tokenization** - needed first"
        ),
        "references_en": [{"title": "Context windows", "url": "https://example.com/context"}],
        "references_ko": [{"title": "Context windows", "url": "https://example.com/context"}],
    }

    issues = _build_handbook_remediation_issues(
        data,
        ["unsupported reference claim: 'NVIDIA' is not present in final references"],
    )
    codes = {issue["code"] for issue in issues}

    assert "definition_too_long" in codes
    assert "unsupported_reference_claim" in codes
    assert "ko_related_tag_mismatch" in codes
    assert "code_not_isomorphic" in codes
    assert any(issue["severity"] == "high" for issue in issues if issue["code"] == "unsupported_reference_claim")


def test_remediation_issues_block_noncanonical_headings_and_bad_related_terms():
    from services.agents.advisor import _build_admin_draft_quality_gate, _build_handbook_remediation_issues

    data = {
        "term_full": "Attention",
        "korean_name": "어텐션",
        "korean_full": "어텐션 메커니즘",
        "term_type": "model_algorithm_family",
        "code_mode_hint": "pseudocode",
        "body_advanced_ko": (
            "## 기술적 정의와 동작 원리\n"
            "설명.\n\n"
            "## 핵심 조건과 운영 포인트\n"
            "임의 제목.\n\n"
            "## 코드 또는 의사코드\n"
            "```python\nprint('x')\n```\n\n"
            "## 프로덕션 체크리스트\n"
            "임의 제목.\n\n"
            "## 실패 모드와 디버깅\n"
            "임의 제목.\n\n"
            "## 설계 패턴\n"
            "임의 제목.\n\n"
            "## 선행·대안·확장 개념\n"
            "- (선행) **Q/K/V** — attention 내부 투영값이라 선행 개념이 아니다.\n"
            "- (확장) **Attention** — 같은 용어라 관련 용어로 쓰면 안 된다."
        ),
        "body_advanced_en": (
            "## Technical Definition & How It Works\n"
            "Details.\n\n"
            "## Key Conditions and Operations\n"
            "Arbitrary heading.\n\n"
            "## Code or Pseudocode\n"
            "```python\nprint('x')\n```\n\n"
            "## Production Checklist\n"
            "Arbitrary heading.\n\n"
            "## Failure Modes and Debugging\n"
            "Arbitrary heading.\n\n"
            "## Design Patterns\n"
            "Arbitrary heading.\n\n"
            "## Prerequisites, Alternatives, and Extensions\n"
            "- (prerequisite) **Q/K/V projections** — an internal attention component.\n"
            "- (extension) **Attention** — the same term, not a related concept."
        ),
    }

    issues = _build_handbook_remediation_issues(data, [])
    codes = {issue["code"] for issue in issues}
    gate = _build_admin_draft_quality_gate(issues, {"status": "pass"})

    assert "advanced_heading_shape_invalid" in codes
    assert "related_term_rule_violation" in codes
    assert gate["status"] == "blocked_for_publish"


def test_remediation_infers_no_code_heading_for_existing_problem_failure_draft():
    from services.agents.advisor import _build_handbook_remediation_issues

    data = {
        "term_full": "Supply-chain attack",
        "korean_full": "공급망 공격(Supply-chain attack)",
        "term_type": "problem_failure_mode",
        "categories": ["safety-ethics"],
        "body_advanced_ko": (
            "## 기술적 정의와 동작 원리\n설명.\n\n"
            "## 핵심 수식·아키텍처·도표\n도표.\n\n"
            "## 운영 패턴과 검수 절차\n절차.\n\n"
            "## 프로덕션 함정\n함정.\n\n"
            "## 트레이드오프와 언제 무엇을 쓰나\n트레이드오프.\n\n"
            "## 업계 대화 맥락\n대화.\n\n"
            "## 선행·대안·확장 개념\n관련 개념."
        ),
        "body_advanced_en": (
            "## Technical Definition & How It Works\nDetails.\n\n"
            "## Formulas, Architecture, and Diagrams\nDiagram.\n\n"
            "## Operational Pattern and Review Procedure\nProcedure.\n\n"
            "## Production Pitfalls\nPitfalls.\n\n"
            "## Tradeoffs — When to Use What\nTradeoffs.\n\n"
            "## Industry Communication\nCommunication.\n\n"
            "## Prerequisites, Alternatives, and Extensions\nRelated concepts."
        ),
    }

    issues = _build_handbook_remediation_issues(data, [])
    codes = {issue["code"] for issue in issues}

    assert "advanced_heading_shape_invalid" not in codes
    assert "advanced_sections_incomplete" not in codes


@pytest.mark.asyncio
async def test_existing_company_draft_hydrates_no_code_metadata_for_remediation():
    from services.agents.advisor import (
        _advanced_sections_for_mode,
        remediate_handbook_draft_content,
    )

    body_advanced_en = "\n\n".join(
        f"{header}\nSection detail."
        for _, header in _advanced_sections_for_mode(
            "en",
            "no-code",
            "product_platform_service",
            "ai_company_ecosystem_actor",
        )
    )
    data = {
        "term": "Mistral AI",
        "term_full": "Mistral AI",
        "categories": ["products-platforms", "llm-genai"],
        "term_type": "product_platform_service",
        "body_advanced_en": body_advanced_en,
    }

    remediated, _, issues, _ = await remediate_handbook_draft_content(
        "Mistral AI",
        data,
        client=MagicMock(),
        apply_llm=False,
    )
    codes = {issue["code"] for issue in issues}

    assert remediated["term_subtype"] == "ai_company_ecosystem_actor"
    assert remediated["code_mode_hint"] == "no-code"
    assert "advanced_heading_shape_invalid" not in codes
    assert "code_not_isomorphic" not in codes


def test_code_isomorphism_does_not_apply_context_window_contract_from_related_terms_only():
    from services.agents.advisor import _build_handbook_remediation_issues

    body_ko = (
        "## 기술적 정의와 동작 원리\n설명.\n\n"
        "## 코드 또는 의사코드\n```python\ndef validate_schema():\n    pass\n```\n\n"
        "## 선행·대안·확장 개념\n- (확장) **Context Window** — 입력 길이 예산과 함께 고려한다."
    )
    body_en = (
        "## Technical Definition & How It Works\nDetails.\n\n"
        "## Code or Pseudocode\n```python\ndef validate_schema():\n    pass\n```\n\n"
        "## Prerequisites, Alternatives, and Extensions\n- (extension) **Context Window** — considered alongside input budget."
    )

    issues = _build_handbook_remediation_issues(
        {
            "term_full": "Structured Outputs",
            "term_type": "capability_feature_spec",
            "code_mode_hint": "pseudocode",
            "body_advanced_ko": body_ko,
            "body_advanced_en": body_en,
        },
        [],
    )

    assert "code_not_isomorphic" not in {issue["code"] for issue in issues}


def test_code_isomorphism_does_not_require_context_window_contract_for_prompt_caching_partial_overlap():
    from services.agents.advisor import _build_handbook_remediation_issues

    code = (
        "```python\n"
        "def preflight_budget():\n"
        "    return {'cached_prefix': True}\n\n"
        "def compact_history():\n"
        "    return ['stable system prompt', 'recent user turn']\n"
        "```\n"
    )

    issues = _build_handbook_remediation_issues(
        {
            "term": "Prompt Caching",
            "term_full": "Prompt Caching",
            "term_type": "capability_feature_spec",
            "code_mode_hint": "pseudocode",
            "body_advanced_ko": f"## 코드 또는 의사코드\n{code}",
            "body_advanced_en": f"## Code or Pseudocode\n{code}",
        },
        [],
    )

    assert "code_not_isomorphic" not in {issue["code"] for issue in issues}


def test_remediation_issues_block_broken_markdown_headings():
    from services.agents.advisor import _build_admin_draft_quality_gate, _build_handbook_remediation_issues

    data = {
        "body_basic_ko": "## 쉽게 이해하기\n첫 섹션입니다. ## 비유와 예시\n둘째 섹션입니다.",
        "body_basic_en": "## Plain Explanation\nFirst section. ## Examples & Analogies\nSecond section.",
        "body_advanced_ko": "## 기술적 정의와 동작 원리\n설명.\n\n## 코드 또는 의사코드```python\nprint('bad')\n```",
        "body_advanced_en": "## Technical Definition & How It Works\nDetails.\n\n## Code or Pseudocode```python\nprint('bad')\n```",
    }

    issues = _build_handbook_remediation_issues(data, [])
    gate = _build_admin_draft_quality_gate(issues, {"status": "pass"})

    assert "markdown_structure_broken" in {issue["code"] for issue in issues}
    assert gate["status"] == "blocked_for_publish"


def test_remediation_issues_block_missing_basic_or_advanced_sections():
    from services.agents.advisor import _build_admin_draft_quality_gate, _build_handbook_remediation_issues

    data = {
        "term_type": "capability_feature_spec",
        "code_mode_hint": "pseudocode",
        "body_basic_ko": "\n\n".join(f"## basic {idx}\ntext" for idx in range(6)),
        "body_basic_en": "\n\n".join(f"## basic {idx}\ntext" for idx in range(7)),
        "body_advanced_ko": "\n\n".join(f"## advanced {idx}\ntext" for idx in range(4)),
        "body_advanced_en": "\n\n".join(f"## advanced {idx}\ntext" for idx in range(4)),
    }

    issues = _build_handbook_remediation_issues(data, [])
    gate = _build_admin_draft_quality_gate(issues, {"status": "pass"})
    codes = {issue["code"] for issue in issues}

    assert "basic_sections_incomplete" in codes
    assert "advanced_sections_incomplete" in codes
    assert gate["status"] == "blocked_for_publish"


def test_unsupported_claim_sentence_remover_deletes_claim_sentences_only():
    from services.agents.advisor import _remove_unsupported_reference_claim_sentences

    data = {
        "body_advanced_en": (
            "NVIDIA defines input sequence length this way. "
            "Keep this grounded mechanism sentence. "
            "A benchmark reports F1 44.9% for this setup."
        ),
        "references_en": [{"title": "Context windows", "url": "https://example.com/context"}],
        "references_ko": [],
    }

    removed = _remove_unsupported_reference_claim_sentences(data)

    assert removed == ["NVIDIA", "F1 44.9%"]
    assert "NVIDIA" not in data["body_advanced_en"]
    assert "F1 44.9%" not in data["body_advanced_en"]
    assert "Keep this grounded mechanism sentence." in data["body_advanced_en"]


def test_unsupported_claim_remover_generalizes_model_names_inside_code_fences():
    from services.agents.advisor import _remove_unsupported_reference_claim_sentences

    data = {
        "body_advanced_en": (
            "```python\n"
            "payload = {'model': 'gpt-5.5'}\n"
            "```\n"
        ),
        "references_en": [{"title": "Prompt caching", "url": "https://example.com/docs"}],
        "references_ko": [],
    }

    removed = _remove_unsupported_reference_claim_sentences(data)

    assert removed == ["gpt-5.5"]
    assert "gpt-5.5" not in data["body_advanced_en"].lower()
    assert "your-model" in data["body_advanced_en"]


def test_admin_draft_quality_gate_uses_highest_remaining_issue_severity():
    from services.agents.advisor import _build_admin_draft_quality_gate

    blocked = _build_admin_draft_quality_gate(
        [{"code": "unsupported_reference_claim", "severity": "high"}],
        {"status": "pass"},
    )
    needs_work = _build_admin_draft_quality_gate(
        [{"code": "definition_too_long", "severity": "medium"}],
        {"status": "pass"},
    )
    ready = _build_admin_draft_quality_gate([], {"status": "pass"})

    assert blocked["status"] == "blocked_for_publish"
    assert needs_work["status"] == "needs_remediation"
    assert ready["status"] == "admin_ready"


@pytest.mark.asyncio
async def test_rescore_existing_handbook_quality_structural_only_uses_current_draft():
    from services.agents.advisor import (
        ADVANCED_SECTIONS_EN,
        ADVANCED_SECTIONS_KO,
        BASIC_SECTIONS_EN,
        BASIC_SECTIONS_KO,
        rescore_existing_handbook_quality,
    )

    def body(sections):
        return "\n\n".join(
            f"{heading}\nThis section has enough concrete handbook detail for a structural rescore pass."
            for _, heading in sections
        )

    scored, usage, warnings = await rescore_existing_handbook_quality(
        "Prompt Caching",
        {
            "id": "2a973e12-9961-4703-9e1d-10d8fb4a2729",
            "slug": "prompt-caching",
            "term_type": "capability_feature_spec",
            "korean_name": "프롬프트 캐싱",
            "hero_news_context_ko": "반복 입력 비용을 줄이는 캐시 기능입니다.",
            "hero_news_context_en": "A cache feature that reduces repeated prompt input cost.",
            "definition_ko": "프롬프트 캐싱은 반복되는 입력 prefix를 재사용해 비용과 지연을 낮추는 기능이다.",
            "definition_en": "Prompt caching reuses repeated prompt prefixes to reduce input cost and latency.",
            "body_basic_ko": body(BASIC_SECTIONS_KO),
            "body_basic_en": body(BASIC_SECTIONS_EN),
            "body_advanced_ko": body(ADVANCED_SECTIONS_KO),
            "body_advanced_en": body(ADVANCED_SECTIONS_EN),
        },
        client=MagicMock(),
        run_semantic=False,
    )

    assert usage == {}
    assert scored["quality"]["advanced"]["method"] == "structural-only"
    assert scored["quality"]["basic"]["method"] == "structural-only"
    assert isinstance(scored["quality_score"], int)
    assert scored["basic_quality_score"] == scored["quality"]["basic"]["total"]
    assert "_quality_gate" in scored
    assert isinstance(warnings, list)


@pytest.mark.asyncio
async def test_rescore_semantic_basic_keeps_related_tail_visible():
    from services.agents import advisor
    from services.agents.advisor import rescore_existing_handbook_quality

    captured = {}

    async def fake_advanced_quality(*args, **kwargs):
        return 90, {}, {}

    async def fake_basic_quality(term, term_type, basic_content, client):
        captured["basic_content"] = basic_content
        return 90, {}, {}

    body_over_four_k = (
        "## Plain Explanation\n"
        + ("This section keeps enough ordinary learner-facing context. " * 85)
        + "\n\n## Related Reading\n- (next) Tail Marker Visible"
    )

    with (
        patch.object(advisor, "_check_handbook_quality", new=AsyncMock(side_effect=fake_advanced_quality)),
        patch.object(advisor, "_check_basic_quality", new=AsyncMock(side_effect=fake_basic_quality)),
    ):
        await rescore_existing_handbook_quality(
            "Reasoning Model",
            {
                "term_type": "system_workflow_pattern",
                "body_basic_ko": body_over_four_k.replace("Plain Explanation", "쉽게 이해하기"),
                "body_basic_en": body_over_four_k,
                "body_advanced_ko": "## 기술적 정의와 동작 원리\n내용",
                "body_advanced_en": "## Technical Definition & How It Works\nContent",
            },
            client=MagicMock(),
            run_semantic=True,
        )

    assert "Tail Marker Visible" in captured["basic_content"]


@pytest.mark.asyncio
async def test_rescore_semantic_advanced_keeps_related_tail_visible():
    from services.agents import advisor
    from services.agents.advisor import rescore_existing_handbook_quality

    captured = {}

    async def fake_advanced_quality(term, term_type, advanced_content, client):
        captured["advanced_content"] = advanced_content
        return 90, {}, {}

    async def fake_basic_quality(*args, **kwargs):
        return 90, {}, {}

    advanced_over_eight_k = (
        "## Technical Definition & How It Works\n"
        + ("This section keeps enough advanced mechanism context. " * 170)
        + "\n\n## Prerequisites, Alternatives, and Extensions\n- (extension) Advanced Tail Marker Visible"
    )

    with (
        patch.object(advisor, "_check_handbook_quality", new=AsyncMock(side_effect=fake_advanced_quality)),
        patch.object(advisor, "_check_basic_quality", new=AsyncMock(side_effect=fake_basic_quality)),
    ):
        await rescore_existing_handbook_quality(
            "Reasoning Model",
            {
                "term_type": "system_workflow_pattern",
                "body_basic_ko": "## 쉽게 이해하기\n내용",
                "body_basic_en": "## Plain Explanation\nContent",
                "body_advanced_ko": advanced_over_eight_k.replace(
                    "Technical Definition & How It Works",
                    "기술적 정의와 동작 원리",
                ),
                "body_advanced_en": advanced_over_eight_k,
            },
            client=MagicMock(),
            run_semantic=True,
        )

    assert "Advanced Tail Marker Visible" in captured["advanced_content"]


def test_record_handbook_quality_scores_uses_existing_slug_and_id():
    from services.agents.advisor import _record_handbook_quality_scores

    class FakeTable:
        def __init__(self, rows):
            self.rows = rows

        def insert(self, row):
            self.rows.append(row)
            return self

        def execute(self):
            return MagicMock(data=[self.rows[-1]])

    class FakeSupabase:
        def __init__(self):
            self.rows = []

        def table(self, name):
            assert name == "handbook_quality_scores"
            return FakeTable(self.rows)

    fake = FakeSupabase()
    inserted = _record_handbook_quality_scores(
        fake,
        {
            "id": "88e5175f-184a-45e0-9760-cd12390a0ddf",
            "slug": "structured-outputs",
            "term": "Structured Outputs",
            "term_type": "capability_feature_spec",
            "quality": {
                "advanced": {"total": 88, "grade": "A", "method": "structural-only"},
                "basic": {"total": 91, "grade": "A", "method": "structural-only"},
            },
        },
        source="seed-rescore",
    )

    assert inserted == 2
    assert [row["term_slug"] for row in fake.rows] == ["structured-outputs", "structured-outputs"]
    assert {row["term_id"] for row in fake.rows} == {"88e5175f-184a-45e0-9760-cd12390a0ddf"}
    assert [row["breakdown"]["level"] for row in fake.rows] == ["advanced", "basic"]


def test_weak_reference_set_prevents_admin_ready_for_core_overridden_terms():
    from services.agents.advisor import _build_admin_draft_quality_gate, _build_handbook_remediation_issues

    data = {
        "term_full": "AI Agent",
        "term_type": "foundational_concept",
        "reference_strength": "low",
        "references_ko": [
            {
                "title": "Generic LLM overview",
                "url": "https://example.com/llm-overview",
                "tier": "secondary",
            }
        ],
        "references_en": [
            {
                "title": "Generic LLM overview",
                "url": "https://example.com/llm-overview",
                "tier": "secondary",
            }
        ],
    }

    issues = _build_handbook_remediation_issues(
        data,
        ["refs_ko: 1 items < 3 (-3)", "refs_en: 1 items < 3 (-3)"],
    )
    gate = _build_admin_draft_quality_gate(issues, {"status": "pass"})

    weak_ref_issues = [issue for issue in issues if issue["code"] == "weak_reference_set"]
    assert weak_ref_issues
    assert weak_ref_issues[0]["severity"] == "high"
    assert gate["status"] == "blocked_for_publish"


def test_remediation_prompt_contains_only_targeted_fields():
    from services.agents.advisor import _build_handbook_remediation_user_prompt

    prompt = _build_handbook_remediation_user_prompt(
        "Context Window",
        {
            "definition_en": "This definition is too long.",
            "body_basic_en": "UNRELATED_BASIC_SHOULD_NOT_APPEAR",
            "references_en": [{"title": "Official docs", "url": "https://example.com/docs"}],
        },
        [{"code": "definition_too_long", "severity": "medium", "section": "definition_en"}],
    )

    assert "definition_en" in prompt
    assert "This definition is too long." in prompt
    assert "UNRELATED_BASIC_SHOULD_NOT_APPEAR" not in prompt


def test_remediation_prompt_includes_basic_and_advanced_for_structure_and_claim_issues():
    from services.agents.advisor import _build_handbook_remediation_user_prompt

    prompt = _build_handbook_remediation_user_prompt(
        "Prompt Caching",
        {
            "body_basic_ko": "## 쉽게 이해하기\n본문. ## 비유와 예시\n본문.",
            "body_advanced_ko": "```python\nmodel = 'gpt-5.5'\n```",
            "body_basic_en": "UNRELATED_EN_BASIC_SHOULD_NOT_APPEAR",
        },
        [
            {"code": "markdown_structure_broken", "severity": "high", "section": "body_basic_ko"},
            {
                "code": "unsupported_reference_claim",
                "severity": "high",
                "section": "body_advanced_ko",
                "evidence": {"claim": "gpt-5.5"},
            },
        ],
    )

    assert "body_basic_ko" in prompt
    assert "본문. ## 비유와 예시" in prompt
    assert "body_advanced_ko" in prompt
    assert "model = 'gpt-5.5'" in prompt
    assert "gpt-5.5" in prompt
    assert "UNRELATED_EN_BASIC_SHOULD_NOT_APPEAR" not in prompt


def test_remediation_prompt_rewrites_advanced_as_practical_system_design_depth():
    from services.agents.advisor import _build_handbook_remediation_user_prompt

    prompt = _build_handbook_remediation_user_prompt(
        "AI Agent",
        {
            "body_advanced_ko": "A POMDP-heavy explanation.",
            "body_advanced_en": "A policy-pi-heavy explanation.",
        },
        [
            {"code": "advanced_provider_drift", "severity": "medium", "section": "body_advanced_ko"},
            {"code": "advanced_provider_drift", "severity": "medium", "section": "body_advanced_en"},
        ],
    )

    assert "practical system-design depth" in prompt
    assert "runtime boundaries" in prompt
    assert "component responsibilities" in prompt
    assert "academic formalism" in prompt
    assert "paper taxonomy" in prompt


def test_remediation_prompt_compresses_code_capsules_without_rewriting_whole_advanced():
    from services.agents.advisor import _build_handbook_remediation_user_prompt

    prompt = _build_handbook_remediation_user_prompt(
        "Attention",
        {
            "body_advanced_ko": "## Code or Pseudocode\n```python\n" + "x = 1\n" * 80 + "```",
            "body_advanced_en": "## Code or Pseudocode\n```python\n" + "x = 1\n" * 80 + "```",
        },
        [
            {"code": "code_capsule_too_large", "severity": "medium", "section": "body_advanced_ko"},
            {"code": "code_capsule_too_large", "severity": "medium", "section": "body_advanced_en"},
        ],
    )

    assert "code_capsule_too_large" in prompt
    assert "shorten only the code or pseudocode section" in prompt
    assert "preserve existing markdown headings" in prompt
    assert "do not rewrite non-code sections" in prompt


def test_context_window_override_defines_focus_and_code_contract():
    from services.agents.prompts_handbook_types import get_term_generation_override

    override = get_term_generation_override("Context Window")

    assert override is not None
    focus = override["advanced_focus_guide"]
    contract = override["code_contract_guide"]
    assert "token budget" in focus
    assert "input/output" in focus
    assert "truncation" in focus
    assert "compaction" in focus
    assert "RAG tradeoff" in focus
    assert "attention cost" in focus
    assert "extended thinking" in focus
    assert "minor provider-specific example" in focus
    assert "KO and EN code sections must implement the same system model" in contract
    assert "preflight_budget" in contract
    assert "reserve_output_tokens" in contract
    assert "compact_history" in contract
    assert "fail_fast" in contract


def test_structural_penalties_warn_on_overlong_code_sections():
    from services.agents.advisor import _check_handbook_structural_penalties

    long_code = "```python\n" + "\n".join(f"print({i})" for i in range(700)) + "\n```"
    body = "\n\n".join(
        [
            "## Technical Definition & How It Works\n" + _long_text("mechanism", 30),
            "## Formulas, Architecture, and Diagrams\n" + _long_text("formulas", 30),
            "## Code or Pseudocode\n" + long_code,
            "## Production Pitfalls\n" + _long_text("pitfalls", 30),
            "## Tradeoffs — When to Use What\n" + _long_text("tradeoffs", 30),
            "## Industry Communication\n" + _long_text("comm", 30),
            "## Prerequisites, Alternatives, and Extensions\n- (prerequisite) **JSON Schema** — " + _long_text("related", 10),
        ]
    )

    _, warnings = _check_handbook_structural_penalties(
        {
            "term_type": "capability_feature_spec",
            "body_advanced_en": body,
            "body_advanced_ko": body,
            "body_basic_en": "\n\n".join(f"## h{i}\n{_long_text('basic', 20)}" for i in range(7)),
            "body_basic_ko": "\n\n".join(f"## h{i}\n{_long_text('basic', 20)}" for i in range(7)),
            "definition_en": "Structured outputs constrain model responses to a schema.",
            "definition_ko": "구조화된 출력은 모델 응답을 스키마에 맞춘다.",
            "hero_news_context_en": "one\ntwo\nthree",
            "hero_news_context_ko": "하나\n둘\n셋",
            "references_en": [{"tier": "primary"}, {"tier": "primary"}, {"tier": "secondary"}],
            "references_ko": [{"tier": "primary"}, {"tier": "primary"}, {"tier": "secondary"}],
            "korean_name": "구조화된 출력",
        }
    )

    assert any("code section too long" in warning for warning in warnings)


def test_structural_penalties_warn_on_bloated_capability_code_capsule():
    from services.agents.advisor import _check_handbook_structural_penalties

    bloated_but_under_hard_limit = "```python\npayload = '" + ("x" * 3600) + "'\n```"
    body = "\n\n".join(
        [
            "## Technical Definition & How It Works\n" + _long_text("mechanism", 30),
            "## Formulas, Architecture, and Diagrams\n" + _long_text("formulas", 30),
            "## Code or Pseudocode\n" + bloated_but_under_hard_limit,
            "## Production Pitfalls\n" + _long_text("pitfalls", 30),
            "## Tradeoffs ??When to Use What\n" + _long_text("tradeoffs", 30),
            "## Industry Communication\n" + _long_text("comm", 30),
            "## Prerequisites, Alternatives, and Extensions\n- (prerequisite) **JSON Schema** ??" + _long_text("related", 10),
        ]
    )

    _, warnings = _check_handbook_structural_penalties(
        {
            "term_type": "capability_feature_spec",
            "body_advanced_en": body,
            "body_advanced_ko": body,
            "body_basic_en": "\n\n".join(f"## h{i}\n{_long_text('basic', 20)}" for i in range(7)),
            "body_basic_ko": "\n\n".join(f"## h{i}\n{_long_text('basic', 20)}" for i in range(7)),
            "definition_en": "Structured outputs constrain model responses to a schema.",
            "definition_ko": "Structured outputs constrain model responses to a schema.",
            "hero_news_context_en": "one\ntwo\nthree",
            "hero_news_context_ko": "one\ntwo\nthree",
            "references_en": [{"tier": "primary"}, {"tier": "primary"}, {"tier": "secondary"}],
            "references_ko": [{"tier": "primary"}, {"tier": "primary"}, {"tier": "secondary"}],
            "korean_name": "Structured Outputs",
        }
    )

    assert any("code capsule too large" in warning for warning in warnings)


def test_model_algorithm_code_capsule_line_bloat_becomes_remediation_issue():
    from services.agents.advisor import (
        _build_handbook_remediation_issues,
        _check_handbook_structural_penalties,
    )

    line_bloated_code = "```python\n" + "\n".join(
        f"step_{i} = run_part({i})" for i in range(70)
    ) + "\n```"
    body = "\n\n".join(
        [
            "## Technical Definition & How It Works\n" + _long_text("mechanism", 30),
            "## Formulas, Architecture, and Diagrams\n" + _long_text("formulas", 30),
            "## Code or Pseudocode\n" + line_bloated_code,
            "## Production Pitfalls\n" + _long_text("pitfalls", 30),
            "## Tradeoffs - When to Use What\n" + _long_text("tradeoffs", 30),
            "## Industry Communication\n" + _long_text("comm", 30),
            "## Prerequisites, Alternatives, and Extensions\n- (prerequisite) **Transformer** - "
            + _long_text("related", 10),
        ]
    )
    data = {
        "term_type": "model_algorithm_family",
        "body_advanced_en": body,
        "body_advanced_ko": body,
        "body_basic_en": "\n\n".join(f"## h{i}\n{_long_text('basic', 20)}" for i in range(7)),
        "body_basic_ko": "\n\n".join(f"## h{i}\n{_long_text('basic', 20)}" for i in range(7)),
        "definition_en": "Attention is a neural mechanism.",
        "definition_ko": "Attention is a neural mechanism.",
        "hero_news_context_en": "one\ntwo\nthree",
        "hero_news_context_ko": "one\ntwo\nthree",
        "references_en": [{"tier": "primary"}, {"tier": "primary"}, {"tier": "secondary"}],
        "references_ko": [{"tier": "primary"}, {"tier": "primary"}, {"tier": "secondary"}],
        "korean_name": "Attention",
    }

    _, warnings = _check_handbook_structural_penalties(data)
    issues = _build_handbook_remediation_issues(data, warnings)

    assert any("code capsule too large" in warning for warning in warnings)
    assert any(issue["code"] == "code_capsule_too_large" for issue in issues)


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
async def test_classify_term_type_uses_valid_type_hint_without_llm():
    from services.agents.advisor import _classify_term_type

    client = MagicMock()
    client.chat.completions.create = AsyncMock()

    term_type, subtype, intents, volatility, confidence = await _classify_term_type(
        "Test-Time Compute",
        ["llm-genai"],
        "Seed type says this is a capability, not an infra product.",
        client,
        "test-model",
        term_type_hint="capability_feature_spec",
    )

    assert term_type == "capability_feature_spec"
    assert subtype is None
    assert intents == ["compare", "evaluate"]
    assert volatility == "fast-changing"
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
async def test_classify_company_terms_as_ai_company_ecosystem_actor():
    from services.agents.advisor import _classify_term_type

    client = MagicMock()
    client.chat.completions.create = AsyncMock()

    term_type, subtype, intents, volatility, confidence = await _classify_term_type(
        "Mistral AI",
        ["products-platforms", "llm-genai"],
        "Mistral AI is an AI company known for open-weight and hosted model products.",
        client,
        "test-model",
    )

    assert term_type == "product_platform_service"
    assert subtype == "ai_company_ecosystem_actor"
    assert intents == ["compare", "understand"]
    assert volatility == "fast-changing"
    assert confidence == pytest.approx(1.0)
    client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_classify_model_services_and_managed_cloud_platforms_from_overrides():
    from services.agents.advisor import _classify_term_type

    client = MagicMock()
    client.chat.completions.create = AsyncMock()

    claude = await _classify_term_type(
        "Claude",
        ["products-platforms", "llm-genai"],
        "Claude is Anthropic's model and API service.",
        client,
        "test-model",
    )
    gemini = await _classify_term_type(
        "Gemini",
        ["products-platforms", "llm-genai"],
        "Gemini is Google's model and API service.",
        client,
        "test-model",
    )
    bedrock = await _classify_term_type(
        "Amazon Bedrock",
        ["products-platforms", "infra-hardware"],
        "Amazon Bedrock is a managed cloud platform for foundation models.",
        client,
        "test-model",
    )

    assert claude[0] == "product_platform_service"
    assert claude[1] == "model_api_service"
    assert gemini[0] == "product_platform_service"
    assert gemini[1] == "model_api_service"
    assert bedrock[0] == "product_platform_service"
    assert bedrock[1] == "managed_ai_cloud_platform"
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
async def test_classify_core_handbook_terms_from_known_overrides_without_llm():
    from services.agents.advisor import _classify_term_type

    client = MagicMock()
    client.chat.completions.create = AsyncMock()

    gpu = await _classify_term_type(
        "GPU",
        ["infra-hardware", "deep-learning"],
        "GPU acceleration is central to deep learning training and inference.",
        client,
        "test-model",
    )
    llm = await _classify_term_type(
        "Large Language Model",
        ["llm-genai", "deep-learning"],
        "Large language models are transformer-based model families for language tasks.",
        client,
        "test-model",
    )
    attention = await _classify_term_type(
        "Attention",
        ["deep-learning", "llm-genai"],
        "Attention is the sequence modeling mechanism behind transformers.",
        client,
        "test-model",
    )

    assert gpu[0] == "hardware_runtime_infra"
    assert gpu[1] == "accelerator_hardware"
    assert gpu[2] == ["compare", "build"]
    assert gpu[3] == "fast-changing"
    assert llm[0] == "model_algorithm_family"
    assert llm[1] is None
    assert llm[2] == ["understand", "compare"]
    assert llm[3] == "fast-changing"
    assert attention[0] == "model_algorithm_family"
    assert attention[1] is None
    assert attention[2] == ["understand", "compare"]
    assert attention[3] == "stable"
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
    from services.agents.prompts_handbook_types import (
        build_artifact_policy_block,
        get_section_weight_guide,
        get_type_basic_guide,
    )

    hardware_guide = get_type_basic_guide("hardware_runtime_infra", "accelerator_hardware")
    company_guide = get_type_basic_guide("product_platform_service", "ai_company_ecosystem_actor")
    company_artifact = build_artifact_policy_block(
        "product_platform_service",
        "ai_company_ecosystem_actor",
        "products-platforms",
        "no-code",
    )
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
    assert "product_platform_service / ai_company_ecosystem_actor" in company_guide
    assert "why this company matters" in company_guide.lower()
    assert "Do NOT output fenced code" in company_artifact
    assert "vendor/adoption review checklist" in company_artifact
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
    assert "<basic_focus>" in first_call_system_prompt
    assert "<advanced_focus>" in first_call_system_prompt
    assert "migration cost" in first_call_system_prompt

    assert result["term_type"] == "product_platform_service"
    assert result["term_subtype"] == "ecosystem_platform"
    assert result["facet_intent"] == ["compare"]
    assert result["facet_volatility"] == "fast-changing"


@pytest.mark.asyncio
async def test_generate_term_tolerates_structured_section_values_in_critique_previews():
    from services.agents.advisor import _run_generate_term

    basic_ko = _basic_ko_payload()
    basic_ko["basic_ko_7_related"] = {
        "prerequisites": [{"term": "Attention", "why": "Needed for context."}],
        "alternatives": [],
        "extensions": [{"term": "Prompt Engineering", "why": "Applies the concept."}],
    }
    advanced_ko = _advanced_ko_payload()
    advanced_ko["adv_ko_7_related"] = {
        "prerequisites": [{"term": "Transformer", "why": "Base architecture."}],
        "alternatives": [],
        "extensions": [{"term": "Agent Loop", "why": "System extension."}],
    }
    advanced_en = _advanced_en_payload()
    advanced_en["adv_en_7_related"] = {
        "prerequisites": [{"term": "Transformer", "why": "Base architecture."}],
        "alternatives": [],
        "extensions": [{"term": "Agent Loop", "why": "System extension."}],
    }

    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        side_effect=[
            _mock_openai_response(basic_ko),
            _mock_openai_response(_basic_en_payload()),
            _mock_openai_response(advanced_ko),
            _mock_openai_response(advanced_en),
        ]
    )

    req = HandbookAdviseRequest(
        action="generate",
        term_id="term-structured",
        term="In-Context Learning",
        categories=["llm-genai"],
        skip_quality_check=True,
    )

    with (
        patch("services.agents.advisor.get_supabase", return_value=None),
        patch(
            "services.agents.advisor._classify_term_type",
            new=AsyncMock(return_value=("foundational_concept", None, ["understand"], "stable", 0.9)),
        ),
        patch("services.agents.advisor._search_term_context", new=AsyncMock(return_value="")),
        patch("services.agents.advisor._search_brave_context", new=AsyncMock(return_value="")),
        patch("services.agents.advisor._search_deep_context", new=AsyncMock(return_value="")),
        patch(
            "services.agents.advisor._build_code_mode_metadata",
            return_value={
                "code_mode_hint": "no-code",
                "mechanism_summary": "Structured section values should not break critique previews.",
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

    assert result["term_type"] == "foundational_concept"
    assert client.chat.completions.create.await_count == 4


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
    assert decide_code_mode("foundational_concept", "policy_discourse", "high", True, True, False) == "no-code"
    assert decide_code_mode("foundational_concept", "standard_regulation", "high", True, True, False) == "no-code"
    assert decide_code_mode("retrieval_knowledge_system", None, "medium", False, True, False) == "pseudocode"
    assert decide_code_mode("capability_feature_spec", None, "high", True, True, False) == "real-code"
    assert decide_code_mode("capability_feature_spec", None, "high", True, True, True) == "no-code"


def test_artifact_policy_block_overrides_generic_code_formula_pressure():
    from services.agents.prompts_handbook_types import build_artifact_policy_block

    block = build_artifact_policy_block(
        "problem_failure_mode",
        None,
        "safety-ethics",
        "no-code",
    )

    assert "overrides generic Advanced instructions" in block
    assert "Do NOT output fenced code" in block
    assert "incident taxonomy" in block
    assert "detection workflow" in block
    assert "mitigation matrix" in block
    assert "Do NOT output adv_ko_specs or adv_en_specs" in block


def test_category_block_adds_category_writing_guides_for_safety_terms():
    from services.agents.prompts_handbook_types import build_category_block

    block = build_category_block("safety-ethics")

    assert "## Domain Context: safety-ethics" in block
    assert "<basic_focus>" in block
    assert "<advanced_focus>" in block
    assert "<good_artifacts>" in block
    assert "<forbidden_patterns>" in block
    assert "<example_style>" in block
    assert "threat model" in block
    assert "incident timeline" in block
    assert "purely philosophical" in block


def test_category_block_adds_product_platform_version_and_marketing_rules():
    from services.agents.prompts_handbook_types import build_category_block

    block = build_category_block("products-platforms")

    assert "pricing" in block
    assert "rate limits" in block
    assert "migration cost" in block
    assert "Do not repeat vendor marketing" in block
    assert "version/date" in block


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


def test_assemble_all_sections_renames_code_header_for_no_code_mode():
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
    assert "## 운영 패턴과 검수 절차" in assembled["body_advanced_ko"]
    assert "## Operational Pattern and Review Procedure" in assembled["body_advanced_en"]
    assert assembled["body_advanced_ko"].count("## ") == 7
    assert assembled["body_advanced_en"].count("## ") == 7


def test_assemble_all_sections_normalizes_tradeoff_labels_for_frontend_grid():
    from services.agents.advisor import _assemble_all_sections

    raw_data = {
        "term_full": "Agentic RAG",
        "korean_name": "에이전틱 RAG",
        "korean_full": "에이전틱 RAG",
        "categories": ["llm-genai"],
        "definition_ko": "에이전틱 RAG는 검색 루프를 계획한다.",
        "definition_en": "Agentic RAG plans retrieval loops.",
        "body_advanced_ko": (
            "## 트레이드오프와 언제 무엇을 쓰나\n"
            "적합한 경우:\n"
            "- 복잡한 검색 질의\n"
            "부적합한 경우:\n"
            "- 단순 FAQ\n"
        ),
        "body_advanced_en": (
            "## Tradeoffs — When to Use What\n"
            "Suitable:\n"
            "- Complex retrieval tasks\n"
            "Unsuitable:\n"
            "- Simple FAQs\n"
        ),
    }

    assembled = _assemble_all_sections(raw_data)

    assert "이럴 때 적합:\n\n- 복잡한 검색 질의" in assembled["body_advanced_ko"]
    assert "이럴 때 부적합:\n\n- 단순 FAQ" in assembled["body_advanced_ko"]
    assert "Suitable:\n\n- Complex retrieval tasks" in assembled["body_advanced_en"]
    assert "Unsuitable:\n\n- Simple FAQs" in assembled["body_advanced_en"]


def test_assemble_all_sections_normalizes_related_rows_for_frontend():
    from services.agents.advisor import _assemble_all_sections

    raw_data = {
        "term_full": "OpenAI",
        "korean_name": "오픈AI",
        "korean_full": "오픈AI",
        "categories": ["products-platforms"],
        "definition_ko": "오픈AI는 모델 API 플랫폼이다.",
        "definition_en": "OpenAI is a model API platform.",
        "body_basic_ko": (
            "## 함께 읽으면 좋은 용어\n"
            "- (기초) Function Calling — Responses API에서 도구를 호출하는 방식.\n"
            "- (유사) Chat Completions\n"
            "- (대안) Imagen 3 — 이미지 생성 경로를 비교합니다.\n"
        ),
        "body_basic_en": (
            "## Related Reading\n"
            "- (before) JSON Schema — Format contract for tools.\n"
            "- (next) Agents SDK\n"
        ),
        "body_advanced_ko": (
            "## 선행·대안·확장 개념\n"
            "- 선행: Function Calling, JSON Schema — 도구·구조화 출력 계약의 기반.\n"
            "- 확장: Agents SDK — 에이전트 오케스트레이션으로 확장.\n"
        ),
        "body_advanced_en": (
            "## Prerequisites, Alternatives, and Extensions\n"
            "- Prerequisites: Function Calling, JSON Schema — Base contracts for tools.\n"
            "- Extensions: Realtime API — Voice and streaming interactions.\n"
        ),
    }

    assembled = _assemble_all_sections(raw_data)

    assert "- (기초) **Function Calling** — Responses API에서 도구를 호출하는 방식." in assembled["body_basic_ko"]
    assert "- (유사) **Chat Completions** — 비슷한 선택지와 차이를 비교할 때 함께 보면 좋습니다." in assembled["body_basic_ko"]
    assert "- (유사) **Imagen 3** — 이미지 생성 경로를 비교합니다." in assembled["body_basic_ko"]
    assert "- (before) **JSON Schema** — Format contract for tools." in assembled["body_basic_en"]
    assert "- (next) **Agents SDK** — Read this next to go deeper from the current term." in assembled["body_basic_en"]
    assert "- (선행) **Function Calling** — 도구·구조화 출력 계약의 기반." in assembled["body_advanced_ko"]
    assert "- (선행) **JSON Schema** — 도구·구조화 출력 계약의 기반." in assembled["body_advanced_ko"]
    assert "- (extension) **Realtime API** — Voice and streaming interactions." in assembled["body_advanced_en"]


def test_assemble_all_sections_normalizes_star_related_bullets_for_frontend():
    from services.agents.advisor import _assemble_all_sections

    raw_data = {
        "term_full": "MCP",
        "korean_name": "모델 컨텍스트 프로토콜",
        "definition_ko": "MCP는 AI 앱과 외부 도구를 연결하는 프로토콜이다.",
        "definition_en": "MCP is a protocol for connecting AI apps to external tools.",
        "body_basic_ko": (
            "## 함께 읽으면 좋은 용어\n"
            "* (기초) Function Calling — 구조화된 도구 호출의 기본 패턴.\n"
        ),
        "body_advanced_en": (
            "## Prerequisites, Alternatives, and Extensions\n"
            "* Prerequisite: JSON-RPC — Base message structure.\n"
        ),
    }

    assembled = _assemble_all_sections(raw_data)

    assert "- (기초) **Function Calling** — 구조화된 도구 호출의 기본 패턴." in assembled["body_basic_ko"]
    assert "- (prerequisite) **JSON-RPC** — Base message structure." in assembled["body_advanced_en"]


def test_assemble_all_sections_normalizes_pitfall_markers_for_frontend():
    from services.agents.advisor import _assemble_all_sections

    raw_data = {
        "term_full": "Guardrails",
        "korean_name": "가드레일",
        "definition_ko": "가드레일은 모델 입출력을 런타임에서 검증하는 레이어다.",
        "definition_en": "Guardrails validate model inputs and outputs at runtime.",
        "body_advanced_ko": (
            "## 프로덕션 함정\n"
            "- 실수: 출력만 검사하고 입력의 프롬프트 인젝션 신호를 놓친다 → 해결: 입력 필터와 출력 검증을 함께 둔다.\n"
        ),
        "body_advanced_en": (
            "## Production Pitfalls\n"
            "* Mistake: Allowing unbounded re-ask loops makes latency unpredictable -> Fix: Cap re-asks and escalate unresolved cases.\n"
        ),
    }

    assembled = _assemble_all_sections(raw_data)

    assert "- ❌ 실수: 출력만 검사하고 입력의 프롬프트 인젝션 신호를 놓친다 → ✅ 해결: 입력 필터와 출력 검증을 함께 둔다." in assembled["body_advanced_ko"]
    assert "- ❌ Mistake: Allowing unbounded re-ask loops makes latency unpredictable → ✅ Fix: Cap re-asks and escalate unresolved cases." in assembled["body_advanced_en"]


def test_assemble_all_sections_normalizes_guardrail_tradeoff_aliases():
    from services.agents.advisor import _assemble_all_sections

    raw_data = {
        "term_full": "Guardrails",
        "korean_name": "가드레일",
        "definition_ko": "가드레일은 모델 입출력을 런타임에서 검증하는 레이어다.",
        "definition_en": "Guardrails validate model inputs and outputs at runtime.",
        "body_advanced_ko": (
            "## 트레이드오프와 언제 무엇을 쓰나\n"
            "적합한 경우:\n"
            "- 보안 민감 배포\n"
            "부적합하거나 대안이 더 나은 경우:\n"
            "- 단순 모더레이션\n"
        ),
        "body_advanced_en": (
            "## Tradeoffs — When to Use What\n"
            "Use MCP when:\n"
            "- Multiple AI apps share integrations.\n"
            "Avoid or defer MCP when:\n"
            "- A single app has one simple function.\n"
        ),
    }

    assembled = _assemble_all_sections(raw_data)

    assert "이럴 때 적합:\n\n- 보안 민감 배포" in assembled["body_advanced_ko"]
    assert "이럴 때 부적합:\n\n- 단순 모더레이션" in assembled["body_advanced_ko"]
    assert "Suitable:\n\n- Multiple AI apps share integrations." in assembled["body_advanced_en"]
    assert "Unsuitable:\n\n- A single app has one simple function." in assembled["body_advanced_en"]


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
async def test_generate_term_can_skip_self_critique_and_improvement_passes():
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
    basic_critique = AsyncMock(return_value=(True, True, "rewrite ko", "rewrite en", 40, 40, {}))
    advanced_critique = AsyncMock(return_value=(True, "rewrite advanced", 40, {}))

    req = HandbookAdviseRequest(
        action="generate",
        term_id="term-draft-only",
        term="Context Window",
        categories=["llm-genai"],
        skip_quality_check=True,
        skip_self_critique=True,
        skip_post_generation_checks=True,
    )

    with (
        patch("services.agents.advisor.get_supabase", return_value=None),
        patch(
            "services.agents.advisor._classify_term_type",
            new=AsyncMock(return_value=("capability_feature_spec", None, ["compare"], "fast-changing", 0.92)),
        ),
        patch("services.agents.advisor._search_term_context", new=AsyncMock(return_value="")),
        patch("services.agents.advisor._search_brave_context", new=AsyncMock(return_value="official docs context")),
        patch("services.agents.advisor._search_deep_context", new=AsyncMock(return_value="deep context")),
        patch(
            "services.agents.advisor._build_code_mode_metadata",
            return_value={
                "code_mode_hint": "real-code",
                "mechanism_summary": "The model can read a bounded prompt window.",
                "has_clear_io_contract": True,
                "has_official_spec_signal": True,
                "reference_strength": "high",
                "vendor_lock_in_risk": "medium",
                "insufficient_info_flag": False,
            },
        ),
        patch("services.agents.advisor._self_critique_basic", new=basic_critique),
        patch("services.agents.advisor._self_critique_advanced", new=advanced_critique),
        patch("services.agents.advisor._validate_ref_urls", new=AsyncMock(side_effect=lambda text: text)),
        patch("services.agents.advisor._extract_novel_entities", new=AsyncMock(return_value=["Unexpected Entity"])) as entity_mock,
        patch("services.agents.advisor._check_handbook_structural_penalties", return_value=(0, [])),
    ):
        result, usage, warnings = await _run_generate_term(req, client, "test-model")

    assert client.chat.completions.create.await_count == 4
    for call in client.chat.completions.create.await_args_list:
        assert call.kwargs["reasoning_effort"] == "low"
        assert call.kwargs["max_tokens"] == 12000
        assert "Draft Smoke Mode" in call.kwargs["messages"][0]["content"]
    basic_critique.assert_not_awaited()
    advanced_critique.assert_not_awaited()
    entity_mock.assert_not_awaited()
    assert result["term_type"] == "capability_feature_spec"


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
    assert "## 운영 패턴과 검수 절차" in result["body_advanced_ko"]
    assert "## Operational Pattern and Review Procedure" in result["body_advanced_en"]
    advanced_system_prompts = [
        call.kwargs["messages"][0]["content"]
        for call in client.chat.completions.create.await_args_list
        if "Generate ADVANCED-level" in call.kwargs["messages"][0]["content"]
    ]
    assert advanced_system_prompts
    assert all("Artifact Policy" in prompt for prompt in advanced_system_prompts)
    assert all("Do NOT output fenced code" in prompt for prompt in advanced_system_prompts)


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


def test_ai_agent_generation_override_curates_direct_references_and_practical_focus():
    from services.agents.prompts_handbook_types import get_term_generation_override

    override = get_term_generation_override("AI Agent")

    assert override is not None
    assert override["preferred_code_mode"] == "no-code"
    assert "runtime loop" in override["advanced_focus_guide"].lower()
    assert "orchestrator" in override["advanced_focus_guide"].lower()
    assert "tool boundary" in override["advanced_focus_guide"].lower()
    assert "POMDP" in override["advanced_focus_guide"]
    assert "do not center" in override["advanced_focus_guide"].lower()
    assert "operational review procedure" in override["code_contract_guide"].lower()

    references_en = override["references_en"]
    references_ko = override["references_ko"]
    assert len(references_en) >= 5
    assert len(references_ko) == len(references_en)
    assert [item["title"] for item in references_ko] == [item["title"] for item in references_en]
    assert sum(1 for item in references_en if item["tier"] == "primary") >= 3
    assert any("anthropic.com/engineering/building-effective-agents" in item["url"] for item in references_en)
    assert any("openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents" in item["url"] for item in references_en)
    assert any("cloud.google.com/discover/what-are-ai-agents" in item["url"] for item in references_en)
    assert any("microsoft.com" in item["url"] for item in references_en)


def test_tool_use_generation_override_curates_official_references_and_execution_focus():
    from services.agents.prompts_handbook_types import get_term_generation_override

    override = get_term_generation_override("Tool Use")

    assert override is not None
    assert override["preferred_code_mode"] == "pseudocode"
    assert "model proposes" in override["advanced_focus_guide"].lower()
    assert "host executes" in override["advanced_focus_guide"].lower()
    assert "tool registry" in override["advanced_focus_guide"].lower()
    assert "argument validation" in override["advanced_focus_guide"].lower()
    assert "benchmark taxonomy" in override["advanced_focus_guide"].lower()
    assert "function calling is an api pattern" in override["advanced_focus_guide"].lower()
    assert "glossary-level" in override["advanced_focus_guide"].lower()
    assert "do not make stop_reason" in override["advanced_focus_guide"].lower()
    assert "same tool-use contract" in override["code_contract_guide"].lower()
    assert "same pseudocode steps" in override["code_contract_guide"].lower()

    references_en = override["references_en"]
    references_ko = override["references_ko"]
    assert len(references_en) >= 5
    assert len(references_ko) == len(references_en)
    assert [item["title"] for item in references_ko] == [item["title"] for item in references_en]
    assert sum(1 for item in references_en if item["tier"] == "primary") >= 4
    assert any("docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview" in item["url"] for item in references_en)
    assert any("platform.openai.com/docs/guides/function-calling" in item["url"] for item in references_en)
    assert any("ai.google.dev/gemini-api/docs/function-calling" in item["url"] for item in references_en)
    assert any("modelcontextprotocol.io" in item["url"] for item in references_en)


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

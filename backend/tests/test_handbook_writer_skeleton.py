"""Tests for structured Relations field rendering in _assemble_markdown."""
from services.agents.advisor import (
    ADVANCED_SECTIONS_EN,
    ADVANCED_SECTIONS_KO,
    _advanced_sections_for_mode,
    _assemble_markdown,
)


def test_renders_structured_relations_ko():
    raw = {
        "adv_ko_1_mechanism": "Mechanism content",
        "adv_ko_7_related": {
            "prerequisites": [
                {"term": "Self-Attention", "relationship": "Q·K^T 내적이 RoPE의 전제"}
            ],
            "alternatives": [
                {"term": "Sinusoidal PE", "relationship": "절대 위치, 일반화 약함"}
            ],
            "extensions": [
                {"term": "ALiBi", "relationship": "거리 페널티 직접 부여"}
            ],
        },
    }
    md = _assemble_markdown(raw, ADVANCED_SECTIONS_KO)
    assert "- (선행) **Self-Attention** — Q·K^T 내적이 RoPE의 전제" in md
    assert "- (대안) **Sinusoidal PE** — 절대 위치, 일반화 약함" in md
    assert "- (확장) **ALiBi** — 거리 페널티 직접 부여" in md
    assert "## 선행·대안·확장 개념" in md


def test_renders_structured_relations_en():
    raw = {
        "adv_en_7_related": {
            "prerequisites": [{"term": "Seq2Seq", "relationship": "fixed-vector bottleneck"}],
            "alternatives": [{"term": "Mamba", "relationship": "O(n) cost"}],
            "extensions": [{"term": "MoE", "relationship": "expert pool"}],
        },
    }
    md = _assemble_markdown(raw, ADVANCED_SECTIONS_EN)
    assert "- (prerequisite) **Seq2Seq** — fixed-vector bottleneck" in md
    assert "- (alternative) **Mamba** — O(n) cost" in md
    assert "- (extension) **MoE** — expert pool" in md


def test_renders_string_relations_backward_compat():
    """Old markdown blob format is accepted and normalized to canonical tags."""
    raw = {
        "adv_ko_7_related": "- (prerequisite) **Foo** — manually-written prose",
    }
    md = _assemble_markdown(raw, ADVANCED_SECTIONS_KO)
    assert "- (선행) **Foo** — manually-written prose" in md


def test_handles_empty_relations_gracefully():
    raw = {"adv_ko_7_related": {"prerequisites": [], "alternatives": [], "extensions": []}}
    md = _assemble_markdown(raw, ADVANCED_SECTIONS_KO)
    assert "## 선행·대안·확장 개념" not in md


def test_handles_partial_relations():
    raw = {
        "adv_ko_7_related": {
            "prerequisites": [{"term": "X", "relationship": "Y"}],
            # alternatives + extensions missing keys entirely
        },
    }
    md = _assemble_markdown(raw, ADVANCED_SECTIONS_KO)
    assert "- (선행) **X** — Y" in md


def test_renders_structured_specs_with_values_and_not_published():
    raw = {
        "adv_ko_specs": {
            "parameters": "175B",
            "context_window": "not_published",
            "training_data": "300B tokens",
            "compute_cost": "not_published",
            "latency_throughput": "not_published",
            "benchmarks": [
                {"name": "MMLU", "score": "65.3%", "context": "5-shot, original paper Table 4"},
            ],
        },
    }
    sections = _advanced_sections_for_mode("ko", "real-code", "product_platform_service", "model_api_service")
    md = _assemble_markdown(raw, sections)
    assert "## 핵심 한도·가격·운영 스펙" in md
    assert "- **Parameters**: 175B" in md
    assert "- **Training data**: 300B tokens" in md
    assert "not published" not in md
    assert "- MMLU: 65.3% — 5-shot, original paper Table 4" in md


def test_renders_specs_with_no_benchmarks():
    raw = {
        "adv_en_specs": {
            "parameters": "8B",
            "benchmarks": [],
        },
    }
    sections = _advanced_sections_for_mode("en", "real-code", "product_platform_service", "model_api_service")
    md = _assemble_markdown(raw, sections)
    assert "Parameters**: 8B" in md
    assert "none reported in original paper" not in md


def test_specs_section_omitted_when_all_fields_empty():
    raw = {"adv_ko_specs": {}}
    sections = _advanced_sections_for_mode("ko", "real-code", "product_platform_service", "model_api_service")
    md = _assemble_markdown(raw, sections)
    assert "## 핵심 한도·가격·운영 스펙" not in md

"""Tests for structured Relations field rendering in _assemble_markdown."""
from services.agents.advisor import _assemble_markdown, ADVANCED_SECTIONS_KO, ADVANCED_SECTIONS_EN


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
    assert "- (prerequisite) **Self-Attention** — Q·K^T 내적이 RoPE의 전제" in md
    assert "- (alternative) **Sinusoidal PE** — 절대 위치, 일반화 약함" in md
    assert "- (extension) **ALiBi** — 거리 페널티 직접 부여" in md
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
    """Old format (markdown blob) still renders verbatim."""
    raw = {
        "adv_ko_7_related": "- (prerequisite) **Foo** — manually-written prose",
    }
    md = _assemble_markdown(raw, ADVANCED_SECTIONS_KO)
    assert "- (prerequisite) **Foo** — manually-written prose" in md


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
    assert "- (prerequisite) **X** — Y" in md

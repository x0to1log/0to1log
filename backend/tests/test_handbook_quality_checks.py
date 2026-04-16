from datetime import datetime, timezone

from services.handbook_quality_checks import (
    check_stale_model_comparison,
)


def _term(term_type: str = "model_family", **body) -> dict:
    base = {
        "slug": "test-term",
        "term": "Test Term",
        "term_type": term_type,
        "body_advanced_en": "",
        "body_advanced_ko": "",
        "body_basic_en": "",
        "body_basic_ko": "",
        "published_at": "2026-01-01T00:00:00Z",
    }
    base.update(body)
    return base


# ---------------- 2a: stale_model_comparison ----------------


def test_stale_model_comparison_fails_when_only_stale_mentioned():
    term = _term(body_advanced_en="We compare against GPT-4o and Gemini 1.5.")
    failed, reason = check_stale_model_comparison(term)
    assert failed is True
    assert "GPT-4o" in reason


def test_stale_model_comparison_passes_when_stale_paired_with_current():
    term = _term(body_advanced_en="GPT-4o baseline compared to Claude Opus 4.6 shows ...")
    failed, _ = check_stale_model_comparison(term)
    assert failed is False


def test_stale_model_comparison_passes_when_no_models_mentioned():
    term = _term(body_advanced_en="An attention mechanism uses softmax.")
    failed, _ = check_stale_model_comparison(term)
    assert failed is False

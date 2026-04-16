from datetime import datetime, timezone

from services.handbook_quality_checks import (
    check_dated_claim,
    check_missing_architecture_detail,
    check_missing_paper_reference,
    check_stale_age,
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


# ---------------- 2b: missing_architecture_detail ----------------


def test_architecture_check_fails_for_model_family_without_keywords():
    term = _term(
        term_type="model_family",
        body_advanced_en="A new AI model. It works well on tasks.",
    )
    failed, reason = check_missing_architecture_detail(term)
    assert failed is True
    assert "architecture" in reason.lower()


def test_architecture_check_passes_for_model_family_with_keywords():
    term = _term(
        term_type="model_family",
        body_advanced_en="70B parameters across 80 transformer layers.",
    )
    failed, _ = check_missing_architecture_detail(term)
    assert failed is False


def test_architecture_check_skips_non_required_types():
    term = _term(
        term_type="product_brand",
        body_advanced_en="A chatbot app.",
    )
    failed, _ = check_missing_architecture_detail(term)
    assert failed is False


# ---------------- 2c: missing_paper_reference ----------------


def test_paper_reference_fails_for_research_method_without_link():
    term = _term(
        term_type="research_method",
        body_advanced_en="A method that improves training.",
    )
    failed, _ = check_missing_paper_reference(term)
    assert failed is True


def test_paper_reference_passes_with_arxiv():
    term = _term(
        term_type="research_method",
        body_advanced_en="See https://arxiv.org/abs/2401.12345 for details.",
    )
    failed, _ = check_missing_paper_reference(term)
    assert failed is False


def test_paper_reference_skips_non_research_type():
    term = _term(
        term_type="product_brand",
        body_advanced_en="A product.",
    )
    failed, _ = check_missing_paper_reference(term)
    assert failed is False


# ---------------- 2d: dated_claim ----------------


def test_dated_claim_fails_on_as_of_2024():
    term = _term(body_advanced_en="As of 2024, this model leads benchmarks.")
    failed, reason = check_dated_claim(term)
    assert failed is True
    assert "2024" in reason


def test_dated_claim_fails_on_korean_baseline():
    term = _term(body_advanced_ko="2024 기준 성능은 ...")
    failed, _ = check_dated_claim(term)
    assert failed is True


def test_dated_claim_fails_on_year_with_nyeon_suffix():
    """Regression: code review found `\\b` doesn't match between digit and Hangul,
    so `2024년 기준` was silently missed before the regex was Hangul-aware."""
    term = _term(body_advanced_ko="2024년 기준 성능은 높습니다.")
    failed, _ = check_dated_claim(term)
    assert failed is True


def test_dated_claim_passes_when_no_date_anchor():
    term = _term(body_advanced_en="The model performs well on MMLU.")
    failed, _ = check_dated_claim(term)
    assert failed is False


# ---------------- 2e: stale_age ----------------


def test_stale_age_fails_when_older_than_threshold():
    term = _term(published_at="2025-01-01T00:00:00Z")
    failed, _ = check_stale_age(term, now=datetime(2026, 4, 16, tzinfo=timezone.utc))
    assert failed is True


def test_stale_age_passes_when_recent():
    term = _term(published_at="2026-04-01T00:00:00Z")
    failed, _ = check_stale_age(term, now=datetime(2026, 4, 16, tzinfo=timezone.utc))
    assert failed is False


def test_stale_age_passes_when_no_published_at():
    term = _term(published_at=None)
    failed, _ = check_stale_age(term, now=datetime(2026, 4, 16, tzinfo=timezone.utc))
    assert failed is False


def test_stale_model_comparison_does_not_double_count_gpt4_inside_gpt4o():
    """Regression: before I1 fix, `"GPT-4"` substring-matched inside `"GPT-4o"`,
    polluting the reason with a bare `GPT-4` it never actually saw."""
    term = _term(body_advanced_en="We benchmark GPT-4o against Claude 3 Opus.")
    failed, reason = check_stale_model_comparison(term)
    assert failed is True
    assert "GPT-4o" in reason
    # The bare "GPT-4" must NOT appear as a separate hit (it's inside GPT-4o)
    # Use a guard that's robust to either join style:
    assert "GPT-4," not in reason and not reason.endswith("GPT-4 without any current-gen model")


def test_stale_model_comparison_matches_longest_first_with_turbo():
    """Both GPT-4 Turbo (which contains GPT-4) and GPT-4o present — each reported exactly once."""
    term = _term(body_advanced_en="Compare GPT-4 Turbo and GPT-4o on MMLU.")
    failed, reason = check_stale_model_comparison(term)
    assert failed is True
    assert "GPT-4 Turbo" in reason
    assert "GPT-4o" in reason


def test_stale_age_handles_naive_datetime():
    """Regression: naive ISO strings (no Z, no offset) used to raise TypeError
    on datetime subtraction. Now treated as UTC."""
    term = _term(published_at="2025-01-01T00:00:00")  # no Z
    failed, _ = check_stale_age(term, now=datetime(2026, 4, 16, tzinfo=timezone.utc))
    assert failed is True


def test_stale_age_returns_false_on_non_string_published_at():
    """Defensive: if published_at arrives as a non-string (e.g., already a datetime
    from some Supabase client versions), do not crash."""
    term = _term(published_at=12345)  # int, not str
    failed, _ = check_stale_age(term, now=datetime(2026, 4, 16, tzinfo=timezone.utc))
    assert failed is False

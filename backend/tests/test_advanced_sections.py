"""Test that Advanced section contracts stay policy-driven."""
from services.agents.advisor import (
    ADVANCED_SECTIONS_EN,
    ADVANCED_SECTIONS_KO,
    _advanced_sections_for_mode,
    _expected_advanced_sections,
)


def test_advanced_sections_ko_has_7_entries():
    assert len(ADVANCED_SECTIONS_KO) == 7


def test_advanced_sections_en_has_7_entries():
    assert len(ADVANCED_SECTIONS_EN) == 7


def test_advanced_sections_ko_keys():
    expected = [
        "adv_ko_1_mechanism",
        "adv_ko_2_formulas",
        "adv_ko_3_code",
        "adv_ko_5_pitfalls",
        "adv_ko_4_tradeoffs",
        "adv_ko_6_comm",
        "adv_ko_7_related",
    ]
    assert [k for k, _ in ADVANCED_SECTIONS_KO] == expected


def test_advanced_sections_en_keys():
    expected = [
        "adv_en_1_mechanism",
        "adv_en_2_formulas",
        "adv_en_3_code",
        "adv_en_5_pitfalls",
        "adv_en_4_tradeoffs",
        "adv_en_6_comm",
        "adv_en_7_related",
    ]
    assert [k for k, _ in ADVANCED_SECTIONS_EN] == expected


def test_advanced_warning_threshold_is_seven():
    """Base redesign: Advanced section count is computed from the section policy."""
    assert _expected_advanced_sections("real-code", "problem_failure_mode", None) == 7


def test_advanced_specs_are_inserted_only_for_spec_heavy_types():
    ko_sections = _advanced_sections_for_mode(
        "ko",
        "real-code",
        "product_platform_service",
        "model_api_service",
    )
    en_sections = _advanced_sections_for_mode(
        "en",
        "real-code",
        "product_platform_service",
        "model_api_service",
    )

    assert [key for key, _ in ko_sections][1] == "adv_ko_specs"
    assert [key for key, _ in en_sections][1] == "adv_en_specs"
    assert _expected_advanced_sections("real-code", "product_platform_service", "model_api_service") == 8


def test_no_code_mode_keeps_section_count_but_renames_code_header():
    ko_sections = _advanced_sections_for_mode("ko", "no-code", "problem_failure_mode", None)
    en_sections = _advanced_sections_for_mode("en", "no-code", "problem_failure_mode", None)

    assert len(ko_sections) == 7
    assert len(en_sections) == 7
    assert ("adv_ko_3_code", "## 운영 패턴과 검수 절차") in ko_sections
    assert ("adv_en_3_code", "## Operational Pattern and Review Procedure") in en_sections
    assert "## 코드 또는 의사코드" not in [header for _, header in ko_sections]
    assert "## Code or Pseudocode" not in [header for _, header in en_sections]


def test_advanced_sections_no_legacy_keys():
    """Removed sections: 1_technical, 3_howworks, 5_practical (full form),
    6_why, 8_refs, 9_related, 10_when_to_use, 11_pitfalls."""
    legacy_ko = {
        "adv_ko_1_technical", "adv_ko_3_howworks", "adv_ko_5_practical",
        "adv_ko_6_why", "adv_ko_8_refs", "adv_ko_9_related",
        "adv_ko_10_when_to_use", "adv_ko_11_pitfalls",
    }
    ko_keys = {k for k, _ in ADVANCED_SECTIONS_KO}
    assert legacy_ko.isdisjoint(ko_keys), f"Legacy KO keys leaked: {legacy_ko & ko_keys}"

    legacy_en = {
        "adv_en_1_technical", "adv_en_3_howworks", "adv_en_5_practical",
        "adv_en_6_why", "adv_en_8_refs", "adv_en_9_related",
        "adv_en_10_when_to_use", "adv_en_11_pitfalls",
    }
    en_keys = {k for k, _ in ADVANCED_SECTIONS_EN}
    assert legacy_en.isdisjoint(en_keys), f"Legacy EN keys leaked: {legacy_en & en_keys}"

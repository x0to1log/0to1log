"""Test that ADVANCED_SECTIONS_{KO,EN} match the 7-section redesign (Plan C)."""
from services.agents.advisor import ADVANCED_SECTIONS_KO, ADVANCED_SECTIONS_EN


def test_advanced_sections_ko_has_7_entries():
    assert len(ADVANCED_SECTIONS_KO) == 7


def test_advanced_sections_en_has_7_entries():
    assert len(ADVANCED_SECTIONS_EN) == 7


def test_advanced_sections_ko_keys():
    expected = [
        "adv_ko_1_mechanism",
        "adv_ko_2_formulas",
        "adv_ko_3_code",
        "adv_ko_4_tradeoffs",
        "adv_ko_5_pitfalls",
        "adv_ko_6_comm",
        "adv_ko_7_related",
    ]
    assert [k for k, _ in ADVANCED_SECTIONS_KO] == expected


def test_advanced_sections_en_keys():
    expected = [
        "adv_en_1_mechanism",
        "adv_en_2_formulas",
        "adv_en_3_code",
        "adv_en_4_tradeoffs",
        "adv_en_5_pitfalls",
        "adv_en_6_comm",
        "adv_en_7_related",
    ]
    assert [k for k, _ in ADVANCED_SECTIONS_EN] == expected


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

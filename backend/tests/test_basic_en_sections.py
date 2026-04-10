"""Test that BASIC_SECTIONS_EN matches the 7-section redesign (2026-04-10 / Plan B)."""
from services.agents.advisor import BASIC_SECTIONS_EN


def test_basic_sections_en_has_7_entries():
    assert len(BASIC_SECTIONS_EN) == 7


def test_basic_sections_en_keys_match_redesign():
    expected_keys = [
        "basic_en_1_plain",
        "basic_en_2_example",
        "basic_en_3_glance",
        "basic_en_4_impact",
        "basic_en_5_caution",
        "basic_en_6_comm",
        "basic_en_7_related",
    ]
    actual_keys = [key for key, _header in BASIC_SECTIONS_EN]
    assert actual_keys == expected_keys


def test_basic_sections_en_headers_are_english():
    for _key, header in BASIC_SECTIONS_EN:
        assert header.startswith("## ")
        # No Korean characters in EN section headers
        assert not any("\uac00" <= ch <= "\ud7a3" for ch in header)


def test_basic_sections_en_no_legacy_keys():
    """Removed sections: 0_summary, 4_why, 5_where, 6b_news_context,
    6c_checklist, 8_related, 9_roles, 10_learning_path."""
    legacy = {
        "basic_en_0_summary",
        "basic_en_4_why",
        "basic_en_5_where",
        "basic_en_6b_news_context",
        "basic_en_6c_checklist",
        "basic_en_8_related",
        "basic_en_9_roles",
        "basic_en_10_learning_path",
    }
    actual = {key for key, _header in BASIC_SECTIONS_EN}
    assert legacy.isdisjoint(actual), f"Legacy keys leaked: {legacy & actual}"

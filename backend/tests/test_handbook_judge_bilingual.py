"""Verify bilingual labeling is present in the user message fed to the judge."""
from services.agents.advisor import _build_bilingual_judge_content


def test_builds_labeled_bilingual_content():
    result = _build_bilingual_judge_content("KO body here", "EN body here")
    assert "## Korean (KO)" in result
    assert "## English (EN)" in result
    assert "KO body here" in result
    assert "EN body here" in result
    # KO must appear before EN (stable order for caching)
    assert result.index("## Korean (KO)") < result.index("## English (EN)")


def test_handles_missing_en():
    result = _build_bilingual_judge_content("KO only", "")
    assert "## Korean (KO)" in result
    assert "KO only" in result
    # Missing locale explicitly noted
    assert "## English (EN)" in result
    assert "(no English content provided)" in result


def test_handles_missing_ko():
    result = _build_bilingual_judge_content("", "EN only")
    assert "## Korean (KO)" in result
    assert "(no Korean content provided)" in result
    assert "## English (EN)" in result
    assert "EN only" in result


def test_strips_whitespace_for_comparison():
    result = _build_bilingual_judge_content("  \n\n  ", "EN body")
    assert "(no Korean content provided)" in result
    assert "EN body" in result


def test_truncates_per_locale_when_max_chars_set():
    long_ko = "K" * 5000
    long_en = "E" * 5000
    result = _build_bilingual_judge_content(long_ko, long_en, max_chars_per_locale=1000)
    # Each locale body truncated to 1000 chars (label "Korean (KO)" / "English (EN)"
    # contains its own K/E so we slice the body sections out of the result).
    ko_body_section = result.split("## Korean (KO)\n\n", 1)[1].split("\n\n## English (EN)", 1)[0]
    en_body_section = result.split("## English (EN)\n\n", 1)[1]
    assert len(ko_body_section) == 1000
    assert len(en_body_section) == 1000
    assert ko_body_section.count("K") == 1000
    assert en_body_section.count("E") == 1000
    # Labels still present
    assert "## Korean (KO)" in result
    assert "## English (EN)" in result


def test_no_truncation_when_max_chars_none():
    long_ko = "K" * 5000
    result = _build_bilingual_judge_content(long_ko, "EN body", max_chars_per_locale=None)
    ko_body_section = result.split("## Korean (KO)\n\n", 1)[1].split("\n\n## English (EN)", 1)[0]
    assert len(ko_body_section) == 5000
    assert ko_body_section.count("K") == 5000


def test_truncation_handles_short_content_unchanged():
    result = _build_bilingual_judge_content("short ko", "short en", max_chars_per_locale=1000)
    assert "short ko" in result
    assert "short en" in result

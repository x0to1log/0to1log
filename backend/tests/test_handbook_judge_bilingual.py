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

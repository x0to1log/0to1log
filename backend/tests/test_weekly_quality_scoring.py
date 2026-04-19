"""Unit tests for weekly deterministic quality scoring helpers."""
from services.pipeline import (
    _compute_weekly_structure_score,
    _compute_weekly_traceability_score,
    _compute_weekly_locale_score,
)


def _good_body(with_h3: bool = True) -> str:
    h3 = "### First story\n\n" if with_h3 else ""
    return (
        "## Section A\n\nParagraph one with [1](https://example.com/a).\n\n"
        "## Section B\n\n" + h3 + "Paragraph two with [2](https://example.com/b).\n\n"
        "## Section C\n\nParagraph three with [3](https://example.com/c).\n"
    )


def _good_ko_body(with_h3: bool = True) -> str:
    h3 = "### 첫 번째 뉴스\n\n" if with_h3 else ""
    return (
        "## 섹션 A\n\n단락 하나 [1](https://example.com/a).\n\n"
        "## 섹션 B\n\n" + h3 + "단락 둘 [2](https://example.com/b).\n\n"
        "## 섹션 C\n\n단락 셋 [3](https://example.com/c).\n"
    )


class TestStructureScore:
    def test_all_bodies_present_with_h2_h3(self):
        body = _good_body(with_h3=True)
        score = _compute_weekly_structure_score(body, body, body, body)
        assert score == 15

    def test_missing_h3_deducts_per_body(self):
        # Body with ## but no ### loses -1 per body, 4 bodies = -4
        body = "## Heading\n\nplain paragraph\n"
        score = _compute_weekly_structure_score(body, body, body, body)
        assert score == 15 - 4

    def test_empty_body_deducts_three(self):
        good = _good_body()
        # One empty body: -3
        score = _compute_weekly_structure_score(good, good, good, "")
        assert score == 15 - 3

    def test_all_empty_returns_zero(self):
        score = _compute_weekly_structure_score("", "", "", "")
        # 4 × -3 = -12, floored at 0
        assert score == max(0, 15 - 12)

    def test_no_h2_and_no_h3_deducts_two_per_body(self):
        body = "plain text without any heading"
        score = _compute_weekly_structure_score(body, body, body, body)
        # -1 for no ##, -1 for no ###, × 4 = -8
        assert score == 15 - 8


class TestTraceabilityScore:
    def test_all_cited_gives_15(self):
        body = _good_body()
        score = _compute_weekly_traceability_score(body, body, body, body)
        assert score == 15

    def test_no_citations_gives_zero(self):
        body = "## A\n\nparagraph one\n\n## B\n\nparagraph two\n"
        score = _compute_weekly_traceability_score(body, body, body, body)
        assert score == 0

    def test_half_cited_returns_half(self):
        # 2 paragraphs cited, 2 uncited per body
        body = (
            "## A\n\nparagraph with [1](https://example.com/a).\n\n"
            "## B\n\nparagraph without citation\n\n"
            "## C\n\nparagraph with [2](https://example.com/b).\n\n"
            "## D\n\nparagraph without citation\n"
        )
        score = _compute_weekly_traceability_score(body, body, body, body)
        # Exactly 50% cited → round(15 * 0.5) = 8 (round half to even gives 8 not 7)
        assert 7 <= score <= 8

    def test_all_empty_returns_zero(self):
        assert _compute_weekly_traceability_score("", "", "", "") == 0


class TestLocaleScore:
    def test_symmetric_bodies_with_korean_gives_10(self):
        en = _good_body(with_h3=True)
        ko = _good_ko_body(with_h3=True)
        score = _compute_weekly_locale_score(en, ko, en, ko)
        assert score == 10

    def test_missing_ko_deducts_three_per_persona(self):
        en = _good_body()
        # Expert KO blank, Learner OK → -3
        score = _compute_weekly_locale_score(en, "", en, _good_ko_body())
        assert score == 10 - 3

    def test_both_personas_missing_ko(self):
        en = _good_body()
        score = _compute_weekly_locale_score(en, "", en, "")
        assert score == 10 - 6

    def test_ko_h3_without_hangul_deducts_two(self):
        en = _good_body(with_h3=True)
        # KO body has ### English-only heading
        ko_bad = (
            "## 섹션 A\n\n단락.\n\n"
            "## 섹션 B\n\n### English Only Heading\n\n단락.\n"
        )
        score = _compute_weekly_locale_score(en, ko_bad, en, _good_ko_body())
        # Expert loses 2 for English ###
        assert score == 10 - 2

    def test_section_count_mismatch_deducts(self):
        en_lots = "## A\n\np\n\n## B\n\np\n\n## C\n\np\n\n## D\n\np\n"
        ko_few = "## 가\n\n단락\n"  # 1 section vs 4 sections → diff ≥ 2
        ko_ok = _good_ko_body()
        score = _compute_weekly_locale_score(en_lots, ko_few, en_lots, ko_ok)
        # Expert persona: -2 for section diff (no KO ### so no hangul penalty)
        assert score == 10 - 2

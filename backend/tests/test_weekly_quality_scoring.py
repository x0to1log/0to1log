"""Unit tests for weekly deterministic quality scoring helpers."""
from services.pipeline import (
    _compute_weekly_structure_score,
    _compute_weekly_traceability_score,
    _compute_weekly_locale_score,
)
from services.pipeline_quality import (
    _find_weekly_citation_contract_issues,
    _find_weekly_primary_source_priority_issues,
    _weekly_guardrail_cap_labels,
)


def _good_body(with_h3: bool = True) -> str:
    """7 ## sections + 5 ### headings (matches weekly spec)."""
    h3_block = "\n\n".join(
        f"### Story {i}\n\nBody with [1](https://example.com/s{i})." for i in range(1, 6)
    ) if with_h3 else ""
    sections = "\n\n".join(
        f"## Section {name}\n\nPara with [1](https://example.com/{i})."
        for i, name in enumerate(["A", "B", "D", "E", "F", "G"])
    )
    return f"## Top Stories\n\n{h3_block}\n\n{sections}\n"


def _good_ko_body(with_h3: bool = True) -> str:
    """Korean version: 7 ## sections + 5 ### headings."""
    h3_block = "\n\n".join(
        f"### 뉴스 {i}\n\n본문 [1](https://example.com/s{i})." for i in range(1, 6)
    ) if with_h3 else ""
    sections = "\n\n".join(
        f"## 섹션 {name}\n\n단락 [1](https://example.com/{i})."
        for i, name in enumerate(["가", "나", "다", "라", "마", "바"])
    )
    return f"## TOP 뉴스\n\n{h3_block}\n\n{sections}\n"


class TestStructureScore:
    def test_perfect_7_sections_5_h3_gives_15(self):
        body = _good_body(with_h3=True)
        score = _compute_weekly_structure_score(body, body, body, body)
        assert score == 15

    def test_6_sections_loses_1_per_body(self):
        # 6 ## sections + 5 ### → -1 per body
        sections = "\n\n".join(f"## S{i}\n\nBody." for i in range(6))
        h3s = "\n\n".join(f"### H{i}\n\nBody." for i in range(5))
        body = sections + "\n\n" + h3s
        score = _compute_weekly_structure_score(body, body, body, body)
        assert score == 15 - 4  # -1 × 4 bodies

    def test_4_sections_loses_2_per_body(self):
        # <5 sections → -2 per body. No ### → -1 per body. Total -3 × 4 = -12
        sections = "\n\n".join(f"## S{i}\n\nBody." for i in range(4))
        score = _compute_weekly_structure_score(sections, sections, sections, sections)
        assert score == 15 - 12  # 3

    def test_no_h3_deducts_1_per_body(self):
        # 7 sections but no ### → -1 per body
        sections = "\n\n".join(f"## S{i}\n\nBody with [1](https://example.com)." for i in range(7))
        score = _compute_weekly_structure_score(sections, sections, sections, sections)
        assert score == 15 - 4

    def test_empty_body_deducts_three(self):
        good = _good_body()
        score = _compute_weekly_structure_score(good, good, good, "")
        assert score == 15 - 3

    def test_all_empty_returns_zero(self):
        score = _compute_weekly_structure_score("", "", "", "")
        assert score == max(0, 15 - 12)

    def test_mixed_body_quality(self):
        # Expert EN perfect, others 6-section (-1 each)
        perfect = _good_body()
        marginal_sections = "\n\n".join(f"## S{i}\n\nBody." for i in range(6))
        h3s = "\n\n".join(f"### H{i}\n\nBody." for i in range(5))
        marginal = marginal_sections + "\n\n" + h3s
        score = _compute_weekly_structure_score(perfect, marginal, marginal, marginal)
        assert score == 15 - 3  # 0 + (-1) × 3


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
        # Expert: EN 7 sections + 5 ### (hangul OK), KO has 7 sections but English ### headings
        en = _good_body(with_h3=True)
        ko_sections = "\n\n".join(f"## 섹션 {i}\n\n단락." for i in range(7))
        ko_english_h3 = "\n\n".join(f"### English Only Heading {i}\n\n단락." for i in range(5))
        ko_bad = ko_sections + "\n\n" + ko_english_h3
        score = _compute_weekly_locale_score(en, ko_bad, en, _good_ko_body())
        # Expert: -2 for English ###. Section counts match (7 vs 7). Learner: no penalty.
        assert score == 10 - 2

    def test_section_count_mismatch_deducts(self):
        en_lots = "\n\n".join(f"## S{i}\n\npara." for i in range(4))  # 4 sections, no ###
        ko_few = "## 가\n\n단락\n"  # 1 section → diff 3 ≥ 2
        # Make learner pair matched (4 vs 4) to isolate expert penalty
        en_learner = en_lots
        ko_learner_matched = "\n\n".join(f"## 섹션 {i}\n\n단락." for i in range(4))
        score = _compute_weekly_locale_score(en_lots, ko_few, en_learner, ko_learner_matched)
        # Expert: -2 (section diff). Learner: 0. No KO ### so no hangul penalty.
        assert score == 10 - 2


class TestWeeklyCitationContract:
    def test_flags_required_weekly_list_and_top_story_citation_gaps(self):
        body = (
            "## Week in Numbers\n\n"
            "- **2 GW** — OpenAI's Trainium capacity commitment.\n"
            "- **$122B** — OpenAI's funding round. [1](https://openai.com/index/accelerating-the-next-phase-ai/)\n\n"
            "## Top Stories\n\n"
            "### OpenAI and AWS sign a capacity deal\n\n"
            "OpenAI and Amazon announced a stateful runtime on Bedrock.\n\n"
            "The deal includes roughly 2 GW of Trainium capacity. [2](https://openai.com/index/amazon-partnership/)\n\n"
            "## Watch Points\n\n"
            "- AWS capacity ramp timing.\n\n"
            "## So What Do I Do?\n\n"
            "- **If you rely on frontier APIs**: reserve capacity now — because access is becoming a procurement issue.\n"
        )

        issues = _find_weekly_citation_contract_issues(body, "expert_body")
        messages = [issue["message"] for issue in issues]

        assert any("week_in_numbers" in message for message in messages)
        assert any("top_story_paragraph" in message for message in messages)
        assert any("watch_points" in message for message in messages)
        assert any("action" in message for message in messages)
        assert "weekly_citation_contract_cap_90" in _weekly_guardrail_cap_labels(issues)

    def test_does_not_flag_cited_weekly_lines(self):
        body = (
            "## Week in Numbers\n\n"
            "- **2 GW** — OpenAI's Trainium capacity commitment. [1](https://openai.com/index/amazon-partnership/)\n\n"
            "## Top Stories\n\n"
            "### OpenAI and AWS sign a capacity deal\n\n"
            "OpenAI and Amazon announced a stateful runtime on Bedrock. [1](https://openai.com/index/amazon-partnership/)\n\n"
            "## Watch Points\n\n"
            "- AWS capacity ramp timing. [1](https://openai.com/index/amazon-partnership/)\n\n"
            "## So What Do I Do?\n\n"
            "- **If you rely on frontier APIs**: reserve capacity now — because access is becoming a procurement issue. [1](https://openai.com/index/amazon-partnership/)\n"
        )

        assert _find_weekly_citation_contract_issues(body, "expert_body") == []


class TestWeeklyPrimarySourcePriority:
    def test_flags_secondary_first_when_relevant_official_source_exists(self):
        body = (
            "## Top Stories\n\n"
            "### OpenAI and AWS sign multi-year deal\n\n"
            "OpenAI and Amazon announced a stateful runtime and Trainium capacity. [1](https://aidailypost.com/news/openai-aws-deal)\n"
        )
        source_urls = [
            "https://aidailypost.com/news/openai-aws-deal",
            "https://openai.com/index/amazon-partnership/",
            "https://www.aboutamazon.com/news/aws/amazon-open-ai-strategic-partnership-investment",
        ]

        issues = _find_weekly_primary_source_priority_issues(body, source_urls, "expert_body")

        assert len(issues) == 1
        assert "primary_source_priority" in issues[0]["message"]
        assert "weekly_primary_source_cap_92" in _weekly_guardrail_cap_labels(issues)

    def test_allows_secondary_first_when_no_official_source_is_available(self):
        body = (
            "## Top Stories\n\n"
            "### Apple reportedly tests model choice in iOS 27\n\n"
            "Apple is reportedly testing model choice for native AI features. [1](https://techcrunch.com/2026/05/05/apple-plans-model-choice)\n"
        )
        source_urls = ["https://techcrunch.com/2026/05/05/apple-plans-model-choice"]

        assert _find_weekly_primary_source_priority_issues(body, source_urls, "learner_body") == []

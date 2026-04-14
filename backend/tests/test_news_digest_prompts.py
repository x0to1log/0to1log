from services.agents.prompts_news_pipeline import (
    CLASSIFICATION_SYSTEM_PROMPT,
    QUALITY_CHECK_BUSINESS_EXPERT,
    QUALITY_CHECK_BUSINESS_LEARNER,
    QUALITY_CHECK_RESEARCH_EXPERT,
    QUALITY_CHECK_RESEARCH_LEARNER,
    get_digest_prompt,
)


def test_research_expert_prompt_is_technical_brief():
    prompt = get_digest_prompt("research", "expert", [])

    assert "## LLM & SOTA Models" in prompt
    assert "## Open Source & Repos" in prompt
    assert "## Research Papers" in prompt
    assert "## Why It Matters" in prompt
    assert "## Technical Decision Points" not in prompt
    assert "## Strategic Decisions" not in prompt


def test_research_learner_prompt_stays_curated_not_action_driven():
    prompt = get_digest_prompt("research", "learner", [])

    assert "## LLM & SOTA Models" in prompt
    assert "## Open Source & Repos" in prompt
    assert "## Research Papers" in prompt
    assert "## Why It Matters" in prompt
    assert "## What To Try This Week" not in prompt
    assert "## Action Items" not in prompt
    assert "guided technical digest" in prompt


def test_learner_prompt_requires_plain_language_before_benchmarks():
    prompt = get_digest_prompt("research", "learner", [])

    assert "the first sentence after every `###` heading must explain" in prompt
    assert "before benchmarks, acronyms, or secondary details" in prompt
    assert "must stay fully grounded in the provided sources" in prompt


def test_learner_prompt_allows_compressing_secondary_detail_after_plain_language_opening():
    prompt = get_digest_prompt("research", "learner", [])

    assert "learner may compress secondary benchmark, architecture, or pricing detail" in prompt
    assert "after the plain-language opening" in prompt


def test_business_prompt_keeps_strategy_sections():
    prompt = get_digest_prompt("business", "expert", [])

    assert "## Connecting the Dots" in prompt
    assert "## Strategic Decisions" in prompt


def test_business_expert_prompt_distinguishes_fact_from_inference():
    prompt = get_digest_prompt("business", "expert", [])

    assert "State sourced facts directly." in prompt
    assert "use calibrated language such as" in prompt
    assert "signals, points to, implies, or suggests" in prompt


def test_business_expert_prompt_separates_front_load_from_analysis_sections():
    prompt = get_digest_prompt("business", "expert", [])

    assert "In the headline, excerpt, and first paragraph of each item, lead with sourced facts and only light interpretation." in prompt
    assert "Stronger synthesis belongs in sections like Connecting the Dots and Strategic Decisions." in prompt
    assert "If a claim depends mainly on secondary reporting, keep it out of the headline and excerpt" in prompt


def test_business_expert_prompt_softens_secondary_source_interpretation_in_front_load():
    prompt = get_digest_prompt("business", "expert", [])

    assert 'avoid definitive competitive verbs such as "hits", "undercuts", "wins", "replaces", or "reduces reliance on"' in prompt
    assert 'phrase it with softer language such as "signals", "suggests", "raises pressure on", or "is positioned as"' in prompt


def test_business_prompt_uses_source_metadata_for_front_load_calibration():
    prompt = get_digest_prompt("business", "expert", [])

    assert "PRIMARY sources can support direct factual statements in the headline, excerpt, and first paragraph." in prompt
    assert "SECONDARY or analysis sources should be framed more cautiously in those front-loaded positions." in prompt
    assert "Treat official_platform_asset sources as factual for release details, but keep strategic interpretation one step more cautious than official_site or paper sources." in prompt


def test_business_prompt_makes_front_load_observable_event_first_for_secondary_sources():
    prompt = get_digest_prompt("business", "expert", [])

    assert "If a lead story is supported mostly by SECONDARY, analysis, or official_platform_asset sources, anchor the headline, excerpt, and first paragraph to the observable event first before any market interpretation." in prompt
    assert 'Prefer factual front-load verbs such as "launches", "releases", "announces", "files", "opens", "reviews", "says", or "prices" over dramatic framing.' in prompt
    assert 'Avoid loaded words such as "scramble", "showdown", "takes aim", "shot at", "salvo", or "war" in the headline, excerpt, and first paragraph unless the source itself uses that framing.' in prompt


def test_research_prompt_has_license_sensitive_wording_guard():
    prompt = get_digest_prompt("research", "expert", [])

    assert 'do NOT call it "open-source" or "open source"' in prompt
    assert 'Use "public weights", "weights released", or "released under non-commercial terms" instead.' in prompt


def test_digest_prompt_requires_english_field_purity():
    prompt = get_digest_prompt("research", "expert", [])

    assert "EN FIELD PURITY" in prompt
    assert "The `en` field is a standalone English article." in prompt
    assert "Do not use Hangul anywhere in the English headline, excerpt, section summaries, `###` headings, or body paragraphs." in prompt


def test_digest_prompt_requires_english_only_subheadings_and_checklist():
    prompt = get_digest_prompt("research", "expert", [])

    assert "**EN `###` headings**: MUST be English-only." in prompt
    assert "Good: `### ClawBench: Agent performance on everyday web tasks`" in prompt
    assert "Bad: `### ClawBench: 실사용 웹 과제에서의 에이전트 성능 점검`" in prompt
    assert "Does the `en` field contain any Hangul in the headline, excerpt, `###` headings, or body?" in prompt


def test_classification_prompt_allows_cross_category_overlap_for_dual_significance():
    assert "The same article CAN appear in both categories if relevant to both" in CLASSIFICATION_SYSTEM_PROMPT
    assert "The same article CAN and SHOULD appear in both categories when it has both technical and business significance." in CLASSIFICATION_SYSTEM_PROMPT
    assert "overlap is valuable, not redundant." in CLASSIFICATION_SYSTEM_PROMPT


def test_digest_prompt_reframes_one_line_summary_as_top_story_synthesis():
    prompt = get_digest_prompt("business", "expert", [])

    assert "must be exactly ONE sentence that synthesizes the main pattern or shared shift across today's top 2-3 stories." in prompt
    assert "Do not merely restate a single headline when multiple major stories clearly point to a broader theme." in prompt
    assert "Does it synthesize the common thread or day's main throughline across the top stories" in prompt
    assert "15 English words" not in prompt
    assert "60 Korean chars" not in prompt


def test_learner_prompt_prefers_news_editor_tone_over_chatty_friend_tone():
    prompt = get_digest_prompt("research", "learner", [])

    assert "written news/editorial prose" in prompt
    assert "knowledgeable friend explaining over lunch" not in prompt


def test_business_expert_prompt_uses_editorial_brief_tone_not_private_advisor_tone():
    prompt = get_digest_prompt("business", "expert", [])

    assert "strategic news brief" in prompt
    assert "trusted strategic advisor in a private briefing" not in prompt


def test_quality_prompts_allow_brief_uncited_one_line_summary():
    prompts = [
        QUALITY_CHECK_RESEARCH_EXPERT,
        QUALITY_CHECK_RESEARCH_LEARNER,
        QUALITY_CHECK_BUSINESS_EXPERT,
        QUALITY_CHECK_BUSINESS_LEARNER,
    ]

    for prompt in prompts:
        assert "One-Line Summary may be brief if it clearly synthesizes the day's main throughline." in prompt
        assert "One-Line Summary does not require an inline citation if the body paragraphs are properly cited." in prompt


def test_quality_prompts_require_structured_issue_schema():
    prompts = [
        QUALITY_CHECK_RESEARCH_EXPERT,
        QUALITY_CHECK_RESEARCH_LEARNER,
        QUALITY_CHECK_BUSINESS_EXPERT,
        QUALITY_CHECK_BUSINESS_LEARNER,
    ]

    for prompt in prompts:
        assert '"severity": "major|minor"' in prompt
        assert '"scope": "expert_body|learner_body|frontload|ko|en"' in prompt
        assert '"category": "source|overclaim|accessibility|locale|structure|clarity"' in prompt


def test_quality_prompts_include_severity_rubric_and_scoring_resolution():
    """Severity taxonomy + scoring resolution guidance must be present.

    Without these, LLM judges drift: severity gets applied subjectively and
    body scores saturate at 95-100. Regression guard against accidental
    removal during future prompt edits.
    """
    from services.agents.prompts_news_pipeline import QUALITY_CHECK_FRONTLOAD

    body_prompts = [
        QUALITY_CHECK_RESEARCH_EXPERT,
        QUALITY_CHECK_RESEARCH_LEARNER,
        QUALITY_CHECK_BUSINESS_EXPERT,
        QUALITY_CHECK_BUSINESS_LEARNER,
    ]

    for prompt in body_prompts:
        # Severity rubric
        assert "## Severity rules" in prompt
        assert "Fabrication / hallucination" in prompt
        assert "unsure whether" in prompt  # the "when in doubt → minor" tiebreaker
        assert "AT MOST 5 issues" in prompt
        # Scoring resolution (stops 95-100 saturation on body judges)
        assert "SCORING RESOLUTION" in prompt
        assert "19-21" in prompt  # intermediate tier anchor
        assert "22-23" in prompt

    # Frontload gets severity rubric but NOT scoring resolution: its
    # distribution is already healthy (49-97 observed) so extra calibration
    # would over-penalize.
    assert "## Severity rules" in QUALITY_CHECK_FRONTLOAD
    assert "SCORING RESOLUTION" not in QUALITY_CHECK_FRONTLOAD


def test_learner_title_strategy_keeps_ko_body_editorial_not_conversational():
    prompt = get_digest_prompt("business", "learner", [])

    assert "Tone for body (ko field): written news/editorial prose by default." in prompt
    assert "친근체 (-에요/-습니다), unchanged." not in prompt

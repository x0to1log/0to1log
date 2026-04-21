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

    assert "should synthesize the common pattern across the top 2-3 stories in one sentence." in prompt
    assert "It should not read like a stitched list of headlines." in prompt
    assert "Name the shift, pressure, or pattern that connects the stories." in prompt
    assert "15 English words" not in prompt
    assert "60 Korean chars" not in prompt


def test_learner_prompt_prefers_news_editor_tone_over_chatty_friend_tone():
    prompt = get_digest_prompt("research", "learner", [])

    assert "written news/editorial prose" in prompt
    assert "knowledgeable friend explaining over lunch" not in prompt
    assert "Write the learner version in clear editorial news prose" in prompt
    assert 'Do not write body paragraphs in a friendly spoken "~요" tone.' in prompt


def test_business_expert_prompt_uses_editorial_brief_tone_not_private_advisor_tone():
    prompt = get_digest_prompt("business", "expert", [])

    assert "strategic news brief" in prompt
    assert "trusted strategic advisor in a private briefing" not in prompt
    assert "foreground the concrete market-moving event or decision first" in prompt
    assert "Avoid semicolon headlines or stitched three-story rollups" in prompt


def test_expert_title_strategy_prefers_one_clear_throughline_over_glued_lists():
    prompt = get_digest_prompt("research", "expert", [])

    assert "The frontload should make today's main shift legible quickly" in prompt
    assert "Do not pack too many separate stories into one line." in prompt
    assert "Prefer one clear throughline over a list of 2-3 headlines glued together." in prompt
    assert "Move technical knobs, benchmark details, and specialist phrasing into the body" in prompt


def test_learner_title_strategy_says_what_changed_before_the_mechanism():
    prompt = get_digest_prompt("research", "learner", [])

    assert "Say what changed before naming the technical mechanism." in prompt
    assert "Prefer user-visible or decision-relevant impact before jargon." in prompt
    assert "If a technical term appears, it should not be the first thing the reader has to decode." in prompt


def test_research_prompts_frontload_practical_advance_before_shorthand():
    expert_prompt = get_digest_prompt("research", "expert", [])
    learner_prompt = get_digest_prompt("research", "learner", [])

    for prompt in [expert_prompt, learner_prompt]:
        assert "foreground the practical advance before the technical mechanism." in prompt
        assert "Avoid leading with insider shorthand such as FP8, KV cache, policy routing" in prompt


def test_quality_prompts_allow_brief_uncited_one_line_summary():
    prompts = [
        QUALITY_CHECK_RESEARCH_EXPERT,
        QUALITY_CHECK_RESEARCH_LEARNER,
        QUALITY_CHECK_BUSINESS_EXPERT,
        QUALITY_CHECK_BUSINESS_LEARNER,
    ]

    for prompt in prompts:
        # Rubric v2 (NP-QUALITY-06): phrase kept inline in sub-score descriptions
        # Accept either full form "may be brief if it synthesizes" or short form
        # "may be brief if synthetic" depending on persona.
        assert "One-Line Summary may be brief" in prompt


def test_quality_prompts_require_structured_issue_schema():
    prompts = [
        QUALITY_CHECK_RESEARCH_EXPERT,
        QUALITY_CHECK_RESEARCH_LEARNER,
        QUALITY_CHECK_BUSINESS_EXPERT,
        QUALITY_CHECK_BUSINESS_LEARNER,
    ]

    for prompt in prompts:
        assert '"severity": "major|minor"' in prompt
        # Rubric v2: scope is per-persona subset (expert_body|ko|en or learner_body|ko|en).
        # Require ko + en at minimum, plus one of expert_body / learner_body.
        assert '"scope":' in prompt
        assert "ko|en" in prompt
        assert ("expert_body" in prompt) or ("learner_body" in prompt)
        assert '"category":' in prompt
        # Category enum varies by persona but must include at least source + locale + structure
        for required_category in ("source", "locale", "structure"):
            assert required_category in prompt


def test_digest_writer_prompt_enforces_frontload_locale_parity():
    """Writer prompt must forbid KO frontload from adding facts not in EN.

    Dominant failure mode in 4/8-4/14 rescore was KO headline/excerpt
    adding numbers, rankings, or allegations not present in EN. This
    rule is prevention for that pattern — the code-level penalty check
    (if added later) is detection.
    """
    for digest_type, persona in [
        ("research", "expert"),
        ("research", "learner"),
        ("business", "expert"),
        ("business", "learner"),
    ]:
        prompt = get_digest_prompt(digest_type, persona, [])
        assert "Frontload Locale Parity" in prompt
        # Core rule
        assert "NATURAL TRANSLATIONS" in prompt
        assert "translation, not a rewrite" in prompt or "translation, not" in prompt.lower()
        # Explicit DO NOT list
        assert "DO NOT add to KO" in prompt
        assert "DO NOT omit from KO" in prompt
        # Checklist item
        assert "Frontload locale parity" in prompt


def test_quality_prompts_include_severity_rubric_and_scoring_resolution():
    """Severity taxonomy + scoring resolution guidance must be present.

    Without these, LLM judges drift: severity gets applied subjectively and
    body scores saturate at 95-100. Regression guard against accidental
    removal during future prompt edits.

    NQ-37 (2026-04-21): frontload migrated to v11 format, so it's now tested
    alongside the 4 body prompts on the shared rubric contract. The only
    difference is frontload has no `locale_integrity` sub-dimension (that's
    a body-specific check); frontload uses `fact_parity`/`entity_parity`
    /`phrase_naturalness` for its locale_alignment category instead.
    """
    from services.agents.prompts_news_pipeline import QUALITY_CHECK_FRONTLOAD

    v11_prompts = [
        QUALITY_CHECK_RESEARCH_EXPERT,
        QUALITY_CHECK_RESEARCH_LEARNER,
        QUALITY_CHECK_BUSINESS_EXPERT,
        QUALITY_CHECK_BUSINESS_LEARNER,
        QUALITY_CHECK_FRONTLOAD,
    ]

    for prompt in v11_prompts:
        # Severity rubric (header + fabrication + locale corruption + hard cap)
        assert "## Severity" in prompt
        assert "fabrication" in prompt.lower()
        assert "locale corruption" in prompt.lower()  # NP-QUALITY-06: explicit locale check
        assert "When unsure" in prompt or "minor" in prompt.lower()  # tiebreaker
        assert "≤3 issues" in prompt or "AT MOST 3" in prompt  # hard cap
        assert "Zero is valid" in prompt or "ZERO issues" in prompt  # anti-invention
        # Rubric v2: 0-10 scale anchors (replaces old 0-25 calibration tier anchors)
        assert "Scoring Scale" in prompt
        assert "Exemplary" in prompt  # 10 anchor
        assert "Solid" in prompt      # 7 anchor
        assert "Weak" in prompt       # 4 anchor
        # Evidence requirement (prevents LLM hedging without grounding)
        assert "evidence" in prompt.lower()
        assert "score" in prompt.lower()
        # v11 rubric: no single-number total (code aggregates)
        assert "no total score" in prompt.lower() or "code aggregates" in prompt.lower()

    # Body-specific: locale_integrity sub-dimension (NP-QUALITY-06 key addition)
    for body in v11_prompts[:4]:
        assert "locale_integrity" in body


def test_frontload_prompt_has_v11_ten_subscores():
    """NQ-37: frontload QC v11 format — 10 sub-scores grouped into 4 categories
    (factuality, calibration, clarity, locale_alignment), with evidence required
    per sub-score and no LLM-emitted total.
    """
    from services.agents.prompts_news_pipeline import QUALITY_CHECK_FRONTLOAD

    # 4 category headings
    assert "### Factuality" in QUALITY_CHECK_FRONTLOAD
    assert "### Calibration" in QUALITY_CHECK_FRONTLOAD
    assert "### Clarity" in QUALITY_CHECK_FRONTLOAD
    assert "### Locale Alignment" in QUALITY_CHECK_FRONTLOAD

    # 10 sub-score keys (body ↔ label text AND JSON output schema)
    sub_keys = [
        "number_grounding", "entity_grounding", "claim_grounding",           # factuality (3)
        "claim_strength", "framing_calibration",                             # calibration (2)
        "headline_specificity", "focus_items_informativeness",               # clarity (2)
        "fact_parity", "entity_parity", "phrase_naturalness",                # locale_alignment (3)
    ]
    for k in sub_keys:
        assert k in QUALITY_CHECK_FRONTLOAD, f"missing sub-score key: {k}"

    # Old single-score contract must be gone
    assert '"score": 0-100' not in QUALITY_CHECK_FRONTLOAD
    assert '"subscores"' not in QUALITY_CHECK_FRONTLOAD  # old flat subscores block

    # Forward-looking verb guard surfaces in calibration dimension (aligns with writer guard)
    assert "forward-looking" in QUALITY_CHECK_FRONTLOAD.lower() or "Expect X to Y" in QUALITY_CHECK_FRONTLOAD


def test_learner_title_strategy_keeps_ko_body_editorial_not_conversational():
    prompt = get_digest_prompt("business", "learner", [])

    assert "Use readable editorial news prose, not chatty spoken copy." in prompt
    assert "News sections should default to concise editorial 기사체." in prompt
    assert "친근체 (-에요/-습니다), unchanged." not in prompt

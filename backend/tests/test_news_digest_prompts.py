from services.agents.prompts_news_pipeline import (
    CLASSIFICATION_SYSTEM_PROMPT,
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

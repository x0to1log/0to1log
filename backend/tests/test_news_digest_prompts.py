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


def test_business_prompt_keeps_strategy_sections():
    prompt = get_digest_prompt("business", "expert", [])

    assert "## Connecting the Dots" in prompt
    assert "## Strategic Decisions" in prompt


def test_classification_prompt_prefers_primary_category_before_duplication():
    assert "Prefer assigning each article to ONE primary category." in CLASSIFICATION_SYSTEM_PROMPT
    assert "Duplication is allowed only for major stories with clear technical and market significance." in CLASSIFICATION_SYSTEM_PROMPT

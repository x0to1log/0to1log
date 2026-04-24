"""Guards that every skeleton's Community Pulse section demonstrates the
new linked block-header + linked attribution format."""

import pytest


@pytest.mark.parametrize("constant_name", [
    "BUSINESS_EXPERT_SKELETON",
    "BUSINESS_LEARNER_SKELETON",
    "RESEARCH_EXPERT_SKELETON",
    "RESEARCH_LEARNER_SKELETON",
])
def test_skeleton_cp_section_uses_linked_block_header(constant_name):
    import services.agents.prompts_news_pipeline as prompts

    skeleton = getattr(prompts, constant_name)
    # At least one linked HN block header in EITHER locale (en or ko section)
    assert "**[Hacker News](https://news.ycombinator.com/" in skeleton, (
        f"{constant_name} CP section must show "
        "**[Hacker News](https://news.ycombinator.com/...)** as the block header example"
    )


@pytest.mark.parametrize("constant_name", [
    "BUSINESS_EXPERT_SKELETON",
    "BUSINESS_LEARNER_SKELETON",
    "RESEARCH_EXPERT_SKELETON",
    "RESEARCH_LEARNER_SKELETON",
])
def test_skeleton_cp_section_uses_linked_attribution(constant_name):
    import services.agents.prompts_news_pipeline as prompts

    skeleton = getattr(prompts, constant_name)
    # At least one linked HN attribution
    assert "> — [Hacker News](https://news.ycombinator.com/" in skeleton, (
        f"{constant_name} must show > — [Hacker News](url) attribution example"
    )


@pytest.mark.parametrize("constant_name", [
    "BUSINESS_EXPERT_SKELETON",
    "BUSINESS_LEARNER_SKELETON",
    "RESEARCH_EXPERT_SKELETON",
    "RESEARCH_LEARNER_SKELETON",
])
def test_skeleton_has_no_bare_cp_attribution(constant_name):
    """After Task 4 lands, no skeleton should have the old bare
    `> — Hacker News` or `> — Reddit` pattern as a demonstration —
    that pattern is a last-resort fallback, not the target format."""
    import re
    import services.agents.prompts_news_pipeline as prompts

    skeleton = getattr(prompts, constant_name)
    # Bare attribution = `> — Hacker News` at end of a line (no bracket/paren after)
    bare_hn = re.search(r"^>\s+—\s+Hacker News\s*$", skeleton, re.MULTILINE)
    bare_reddit = re.search(r"^>\s+—\s+Reddit\s*$", skeleton, re.MULTILINE)
    assert bare_hn is None, f"{constant_name} still contains bare `> — Hacker News` attribution"
    assert bare_reddit is None, f"{constant_name} still contains bare `> — Reddit` attribution"

"""Guards that every skeleton's Community Pulse section demonstrates the
new [CITE_N] citation pattern (not the old bold-inline-link format)."""

import re
import pytest


@pytest.mark.parametrize("constant_name", [
    "BUSINESS_EXPERT_SKELETON",
    "BUSINESS_LEARNER_SKELETON",
    "RESEARCH_EXPERT_SKELETON",
    "RESEARCH_LEARNER_SKELETON",
])
def test_skeleton_block_header_ends_with_cite_token(constant_name):
    import services.agents.prompts_news_pipeline as prompts

    skeleton = getattr(prompts, constant_name)
    # At least one block header line ending with [CITE_N]
    assert re.search(r"\*\*(?:Hacker News|r/[^*]+?)\*\*\s*\([^)]+?↑\)\s*—[^\n]+\[CITE_\d+\]", skeleton), (
        f"{constant_name} CP section must show block header ending with [CITE_N] "
        "(pattern: **Label** (N↑) — summary [CITE_N])"
    )


@pytest.mark.parametrize("constant_name", [
    "BUSINESS_EXPERT_SKELETON",
    "BUSINESS_LEARNER_SKELETON",
    "RESEARCH_EXPERT_SKELETON",
    "RESEARCH_LEARNER_SKELETON",
])
def test_skeleton_attribution_ends_with_cite_token(constant_name):
    import services.agents.prompts_news_pipeline as prompts

    skeleton = getattr(prompts, constant_name)
    # At least one attribution line ending with [CITE_N]
    assert re.search(r">\s*—\s*(?:Hacker News|Reddit|r/[^\[\n]+?)\s*\[CITE_\d+\]", skeleton), (
        f"{constant_name} must show attribution ending with [CITE_N] "
        "(pattern: > — Label [CITE_N])"
    )


@pytest.mark.parametrize("constant_name", [
    "BUSINESS_EXPERT_SKELETON",
    "BUSINESS_LEARNER_SKELETON",
    "RESEARCH_EXPERT_SKELETON",
    "RESEARCH_LEARNER_SKELETON",
])
def test_skeleton_has_no_bold_inline_link(constant_name):
    """After Task 4 lands, no skeleton should retain the failed
    `**[Label](URL)**` bold-inline-link format — that's the pattern
    the LLM cannot reliably produce."""
    import services.agents.prompts_news_pipeline as prompts

    skeleton = getattr(prompts, constant_name)
    # Scan only the CP section to avoid false positives from body example links
    cp_match = re.search(r"##\s*(?:Community Pulse|커뮤니티 반응)[\s\S]*?(?=\n##\s|\Z)", skeleton)
    assert cp_match, f"{constant_name} has no CP section"
    cp_body = cp_match.group(0)
    assert "**[Hacker News]" not in cp_body, (
        f"{constant_name} CP still contains old **[Hacker News](url)** pattern"
    )
    assert "**[r/" not in cp_body, (
        f"{constant_name} CP still contains old **[r/subreddit](url)** pattern"
    )


@pytest.mark.parametrize("constant_name", [
    "BUSINESS_EXPERT_SKELETON",
    "BUSINESS_LEARNER_SKELETON",
    "RESEARCH_EXPERT_SKELETON",
    "RESEARCH_LEARNER_SKELETON",
])
def test_skeleton_has_no_bare_attribution(constant_name):
    """Attribution must end with [CITE_N] — bare `> — Hacker News` without
    a citation token would signal pre-plan format. Guard against regression."""
    import re
    import services.agents.prompts_news_pipeline as prompts

    skeleton = getattr(prompts, constant_name)
    cp_match = re.search(r"##\s*(?:Community Pulse|커뮤니티 반응)[\s\S]*?(?=\n##\s|\Z)", skeleton)
    assert cp_match, f"{constant_name} has no CP section"
    cp_body = cp_match.group(0)
    bare = re.search(r"^>\s*—\s*(?:Hacker News|Reddit|r/\S+?)\s*$", cp_body, re.MULTILINE)
    assert bare is None, (
        f"{constant_name} CP still contains bare attribution '{bare.group(0) if bare else ''}' "
        "— must end with [CITE_N]"
    )

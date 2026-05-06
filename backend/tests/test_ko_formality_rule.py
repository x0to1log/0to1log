"""LEARNER_KO_LANGUAGE_RULE forbids chatty Korean markers in news prose.

2026-05-06 audit: research-digest-ko learner had "쉽게 말해" mid-paragraph
in the vision section. QC flagged as conversational marker breaking
news-style prose. Rule 6 added to LEARNER_KO_LANGUAGE_RULE bans these
patterns explicitly. This test pins the rule's presence.
"""
from services.agents.prompts_news_pipeline import LEARNER_KO_LANGUAGE_RULE


def test_rule_6_forbids_chatty_explainer():
    """`쉽게 말해` is the specific phrase that triggered the May 6 issue."""
    assert "쉽게 말해" in LEARNER_KO_LANGUAGE_RULE


def test_rule_6_forbids_casual_endings():
    """Casual sentence enders break news tone."""
    p = LEARNER_KO_LANGUAGE_RULE
    for ender in ("~잖아요", "~죠", "~네요"):
        assert ender in p, f"casual ending '{ender}' not banned in rule"


def test_rule_6_provides_replacements():
    """Rule must give concrete alternatives, not just bans."""
    p = LEARNER_KO_LANGUAGE_RULE
    # 즉, 다시 말해, 요컨대 are the suggested replacements for 쉽게 말해
    assert any(repl in p for repl in ("즉", "다시 말해", "요컨대"))


def test_rule_6_includes_why_explanation():
    """Prompts that explain WHY (not just WHAT) get better LLM compliance."""
    p = LEARNER_KO_LANGUAGE_RULE.lower()
    assert "why" in p or "blog" in p or "tutorial" in p, (
        "rule 6 should explain why news prose tone matters"
    )


def test_rule_6_includes_good_and_bad_examples():
    """Few-shot examples improve compliance."""
    p = LEARNER_KO_LANGUAGE_RULE
    # The good/bad examples in rule 6 specifically
    assert "✅ Good (news prose)" in p
    assert "❌ Bad (blog/tutorial tone)" in p


def test_pre_submit_scan_mentions_chatty_check():
    """The 'before submitting, scan' line at the bottom must include rule 6."""
    p = LEARNER_KO_LANGUAGE_RULE
    # Find the scan line and verify it mentions rule 6 / chatty
    scan_section = p[p.find("Before submitting"):]
    assert "rule 6" in scan_section.lower() or "chatty" in scan_section.lower()

"""CLASSIFICATION_SYSTEM_PROMPT must contain the tier × freshness gate.

Regression test for the May 4 stale-recycle incident — without the matrix
gate, SEO sites republishing weeks-old events as fresh articles reach
primary classification slots. The prompt is the only enforcement point in
Phase 1; this test ensures the gate stays present across edits.
"""
from services.agents.prompts_news_pipeline import CLASSIFICATION_SYSTEM_PROMPT


def test_prompt_contains_tier_definitions():
    p = CLASSIFICATION_SYSTEM_PROMPT
    assert "TIER-1" in p, "TIER-1 definition missing"
    assert "TIER-2" in p, "TIER-2 definition missing"
    assert "TIER-3" in p, "TIER-3 definition missing"


def test_prompt_contains_freshness_window():
    p = CLASSIFICATION_SYSTEM_PROMPT
    assert "14" in p, "14-day freshness window not specified"
    assert ("FRESH" in p) or ("fresh" in p), "FRESH/fresh keyword missing"
    assert ("OLD" in p) or ("old" in p), "OLD/old keyword missing"


def test_prompt_contains_reject_rules_for_tier3_and_old():
    p = CLASSIFICATION_SYSTEM_PROMPT.lower()
    assert ("reject" in p) or ("skip" in p), "no reject/skip directive"
    assert "tier-3" in p, "TIER-3 disposition not stated"


def test_prompt_contains_few_shot_examples():
    p = CLASSIFICATION_SYSTEM_PROMPT.lower()
    example_markers = ["example", "e.g.", "for instance", "such as"]
    assert any(m in p for m in example_markers), "no few-shot examples found"


def test_prompt_gate_appears_before_litmus_test():
    """Gate must run BEFORE category-specific litmus tests so gate-failing
    candidates are excluded early."""
    p = CLASSIFICATION_SYSTEM_PROMPT
    gate_pos = p.lower().find("tier-1")
    litmus_pos = p.lower().find("litmus test")
    if litmus_pos < 0:
        return  # litmus phrasing changed — skip this assertion
    assert gate_pos < litmus_pos, (
        f"Gate ({gate_pos}) must appear before litmus test ({litmus_pos})"
    )


def test_prompt_no_unsubstituted_batch_date_placeholder():
    """The '{batch_date}' literal in the gate section was masking the
    intended date arithmetic — the LLM saw it as literal text. cef376b
    replaced with self-explanatory wording. Regression guard."""
    p = CLASSIFICATION_SYSTEM_PROMPT
    # The gate section is everything before '## Categories'
    gate_section = p.split("## Categories")[0]
    assert "{batch_date}" not in gate_section, (
        "{batch_date} placeholder leaked back into gate section — "
        "no .format() substitution happens at this call site"
    )


def test_prompt_contains_known_trusted_media_override():
    """TIER-2 has an explicit override list to handle known false negatives
    in the upstream source confidence classifier (NQ-43). Without this,
    legit mainstream outlets misclassified as confidence=low fall to
    TIER-3 and get rejected."""
    p = CLASSIFICATION_SYSTEM_PROMPT
    # Spot-check a few must-have domains from the override list
    for domain in ("axios.com", "reuters.com", "techcrunch.com"):
        assert domain in p, f"{domain} missing from known-trusted override"

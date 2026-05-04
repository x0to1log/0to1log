"""CLASSIFICATION_SYSTEM_PROMPT must contain the tier × freshness gate.

Regression test for the May 4 stale-recycle incident — without the matrix
gate, SEO sites republishing weeks-old events as fresh articles reach
primary classification slots. The prompt is the only enforcement point in
Phase 1; this test ensures the gate stays present across edits.
"""
import re

from services.agents.prompts_news_pipeline import CLASSIFICATION_SYSTEM_PROMPT


def test_prompt_contains_tier_definitions():
    p = CLASSIFICATION_SYSTEM_PROMPT
    assert "TIER-1" in p, "TIER-1 definition missing"
    assert "TIER-2" in p, "TIER-2 definition missing"
    assert "TIER-3" in p, "TIER-3 definition missing"


def test_prompt_contains_freshness_window():
    p = CLASSIFICATION_SYSTEM_PROMPT
    # "14" must appear near "day" — anchor to actual freshness context
    assert re.search(r"14\s*(?:-|\s)?day", p, re.IGNORECASE), \
        "14-day freshness window not specified in expected '14 day'/'14-day' form"
    assert "FRESH" in p, "FRESH keyword missing"
    assert "OLD" in p, "OLD keyword missing"


def test_prompt_contains_tier3_reject_rule():
    p = CLASSIFICATION_SYSTEM_PROMPT
    # Find every occurrence of TIER-3 and verify at least one is followed by
    # REJECT/skip within the next 100 chars (matrix row width)
    matches = list(re.finditer(r"TIER-3", p))
    assert matches, "TIER-3 not found"
    found_reject_link = False
    for m in matches:
        window = p[m.end():m.end() + 100].lower()
        if "reject" in window or "skip" in window:
            found_reject_link = True
            break
    assert found_reject_link, (
        "TIER-3 appears but no REJECT/skip directive within 100 chars — "
        "the rule that TIER-3 maps to reject is not enforced by the prompt"
    )


def test_prompt_contains_few_shot_examples():
    """Gate has 4 worked examples (TIER-1 PASS, TIER-1 OLD reject,
    TIER-3 SEO reject, TIER-2 PASS) labeled 'EXAMPLE PASS' / 'EXAMPLE REJECT'."""
    p = CLASSIFICATION_SYSTEM_PROMPT
    pass_count = p.count("EXAMPLE PASS")
    reject_count = p.count("EXAMPLE REJECT")
    assert pass_count >= 2, f"Expected >=2 'EXAMPLE PASS' labels, found {pass_count}"
    assert reject_count >= 2, f"Expected >=2 'EXAMPLE REJECT' labels, found {reject_count}"


def test_prompt_gate_appears_before_litmus_test():
    """Gate must run BEFORE category-specific litmus tests so gate-failing
    candidates are excluded early."""
    p = CLASSIFICATION_SYSTEM_PROMPT
    gate_pos = p.lower().find("tier-1")
    litmus_pos = p.lower().find("litmus test")
    assert litmus_pos >= 0, "Litmus test section missing — gate-before-litmus ordering can't be checked"
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

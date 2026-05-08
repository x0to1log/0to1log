"""Pins May 8 prompt fixes for digest LEARNER quality issues.

2026-05-08 audit (research-digest score 85): two distinct issues found:
  - Fix A: `RAG` appeared bare in EN learner body while KO had `검색 증강 생성(RAG)`.
    Previous rule said "Korean style" with KO-only example, so model read it as
    KO-only. Rule now applies to BOTH locales independently.
  - Fix B: frontload used `13 baselines falter` / `13개 기준 모델이 흔들린다` —
    scope-strength wording without numeric backing. Quality reviewer flagged
    claim_strength 7/10. New section in LEARNER_TITLE_STRATEGY pins this as
    the negative-direction sibling of the existing positive-overclaim ban.

These tests pin the prompt structure so regressions show up at CI time, not
in production after a quality drop.
"""
from services.agents.prompts_news_pipeline import (
    LEARNER_TITLE_STRATEGY,
    RESEARCH_LEARNER_GUIDE,
)


# ---------------------------------------------------------------------------
# Fix A — acronym expansion in BOTH locales
# ---------------------------------------------------------------------------

def test_research_learner_acronym_rule_covers_both_locales():
    """Rule must explicitly say BOTH locales need independent expansion."""
    g = RESEARCH_LEARNER_GUIDE
    # Header marks it as a both-locale rule (catches return-to-KO-only edits)
    assert "BOTH locales" in g
    assert "EN AND independently" in g or "EN reader cannot see the KO" in g


def test_research_learner_acronym_rule_includes_rag_explicitly():
    """RAG was the specific acronym that triggered the May 8 issue."""
    g = RESEARCH_LEARNER_GUIDE
    # In the acronym list
    assert "RAG" in g
    # AND as the canonical EN example
    assert "Retrieval-Augmented Generation (RAG)" in g
    # AND with a KO expansion example
    assert "검색 증강 생성" in g and "RAG" in g


def test_research_learner_acronym_rule_provides_good_and_bad_examples():
    """Few-shot examples improve compliance over abstract rules."""
    g = RESEARCH_LEARNER_GUIDE
    assert "✅" in g and "❌" in g
    # The specific bare-RAG anti-pattern that occurred
    assert "bare RAG" in g.lower() or "RAG or agent features" in g


def test_research_learner_acronym_rule_lists_common_offenders():
    """Specific acronyms anchor 'what counts'. List is intentionally short
    (representative, not exhaustive) so the model generalizes via the rule
    rather than treating the list as a closed set."""
    g = RESEARCH_LEARNER_GUIDE
    # Highest-frequency learner-confusing offenders that MUST stay in the list
    for acr in ("LLM", "MoE", "RLHF", "DPO", "CoT", "SFT", "MCP"):
        assert acr in g, f"core acronym {acr!r} missing from list"


def test_research_learner_acronym_rule_marks_list_as_representative():
    """A short list works only if the model treats it as 'examples, not
    exhaustive' — otherwise it caps the rule's coverage to listed items."""
    g = RESEARCH_LEARNER_GUIDE
    assert "examples, not exhaustive" in g or "Representative acronyms" in g


def test_research_learner_acronym_rule_no_duplicate_agi():
    """May 8 first draft listed AGI twice — pin against re-introducing typos."""
    g = RESEARCH_LEARNER_GUIDE
    # Only worry about the acronym section — split on the section header
    section_start = g.find("Acronym expansion")
    section_end = g.find("\n- ", section_start + 1)
    section = g[section_start:section_end] if section_end > 0 else g[section_start:]
    # No acronym should appear twice in the listing line
    listing_line = next(
        (line for line in section.split("\n") if "REQUIRE expansion" in line),
        "",
    )
    # AGI is the typical regression case; check no acronym repeats
    for acr in ("AGI", "RAG", "LLM", "MoE"):
        assert listing_line.count(acr) <= 1, f"{acr!r} appears twice in list"


def test_research_learner_acronym_rule_explains_why():
    """Prompt-engineering best practice: explain WHY the rule exists.
    Models comply more reliably when they understand the constraint."""
    g = RESEARCH_LEARNER_GUIDE.lower()
    assert "why:" in g
    # Specific reason for May 8 fix
    assert "ko-only" in g or "accessibility" in g


# ---------------------------------------------------------------------------
# Fix B — calibrated scope/scale claims in frontload
# ---------------------------------------------------------------------------

def test_learner_title_strategy_has_scope_calibration_section():
    """New section pins the 'falter / 흔들린다' anti-pattern."""
    s = LEARNER_TITLE_STRATEGY
    assert "Calibrated scope/scale claims" in s
    assert "falter" in s
    assert "흔들린다" in s


def test_learner_title_strategy_calibration_provides_specific_alternatives():
    """The cure for overclaim is specific numbers, not just 'don't say falter'."""
    s = LEARNER_TITLE_STRATEGY
    # Rule must show how to rewrite, not just what to ban
    assert "13 of 25 baselines" in s or "score below 50%" in s
    # KO replacement parallel
    assert "50% 미만" in s or "X포인트 뒤처짐" in s


def test_learner_title_strategy_calibration_has_good_and_bad_examples():
    """Side-by-side ✅/❌ pairs are the teaching mechanism."""
    s = LEARNER_TITLE_STRATEGY
    # The exact May 8 anti-pattern in the ❌ block
    assert "13 baselines falter" in s
    assert "13개 기준 모델이 핵심 조작" in s or "13개 기준 모델이 흔들린다" in s


def test_learner_title_strategy_calibration_softening_path():
    """When numeric backing is missing, the rule must offer a softer path
    rather than forcing model into the bad alternative of just removing the
    claim entirely."""
    s = LEARNER_TITLE_STRATEGY
    assert "softening" in s.lower() or "Acceptable softening" in s
    # Bidirectional: gives both EN and KO softening mappings
    assert "show gaps" in s.lower() or "trail" in s.lower()
    assert "격차를 보임" in s or "뒤처짐" in s


def test_learner_title_strategy_pre_submit_scan_covers_both_fixes():
    """Pattern from rule 6 (KO formality): pre-submit checklist enforces
    rules at the end. Both fixes (acronym + scope) must be in scan."""
    s = LEARNER_TITLE_STRATEGY
    # Find the scan block
    assert "Pre-submit scan" in s
    scan_section = s[s.find("Pre-submit scan"):]
    # Acronym check is in the scan
    assert "Acronym" in scan_section or "acronym" in scan_section
    # Scope/scale check is in the scan
    assert "scope" in scan_section.lower() or "Scope/scale" in scan_section


def test_learner_title_strategy_calibration_acknowledges_negative_direction():
    """Existing body-level ban targets positive overclaim (dominates/장악).
    The new rule must explicitly cover the inverse (falter/흔들린다) and
    explain the symmetry — otherwise a future reader may delete it as
    duplicating the existing rule."""
    s = LEARNER_TITLE_STRATEGY
    assert "negative-direction" in s
    # Mentions the existing positive ban so reader sees they are paired
    assert "dominates" in s or "장악" in s or "석권" in s

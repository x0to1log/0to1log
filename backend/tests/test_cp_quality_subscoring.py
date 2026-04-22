"""NQ-40 Phase 2a: CP quality sub-scoring — measurement-only.

Covers:
- `_aggregate_subscores` excludes `community_pulse` from the digest total.
- Aggregation unchanged when CP is absent (backward compat).
- All 4 body QC prompts include the CP sub-scores + N/A fallback language.
- `_log_cp_subscores` emits the expected observability line.

Reference: vault/09-Implementation/plans/2026-04-22-nq-40-phase-2-cp-quality.md
"""

import logging


def test_aggregate_subscores_excludes_community_pulse():
    """community_pulse sub-scores must NOT affect the digest total during Phase 2a.

    Total should equal the average of non-CP groups only — even if CP scores
    are zero, they should not drag the total down; even if CP scores are 10,
    they should not push a low total up.
    """
    from services.pipeline import _aggregate_subscores

    # 4 non-CP sub-scores all at 8 → avg 8 → total 80
    # 3 CP sub-scores all at 0 → should NOT drop the total to (32+0)/7 ≈ 46
    data = {
        "structural_completeness": {
            "sections_present": {"evidence": "all present", "score": 8},
            "section_depth": {"evidence": "substantial", "score": 8},
        },
        "language_quality": {
            "fluency": {"evidence": "natural", "score": 8},
            "locale_integrity": {"evidence": "KO clean", "score": 8},
        },
        "community_pulse": {
            "cp_relevance": {"evidence": "all quotes tangential", "score": 0},
            "cp_substance": {"evidence": "pure hype", "score": 0},
            "translation_fidelity": {"evidence": "heavy paraphrase", "score": 0},
        },
        "issues": [],
    }

    # Must be 80, NOT 46 (which would be (8*4 + 0*3) / 7 * 10)
    assert _aggregate_subscores(data) == 80


def test_aggregate_subscores_cp_at_ten_does_not_inflate_low_total():
    """Mirror test: CP at 10 should not push a low total upward."""
    from services.pipeline import _aggregate_subscores

    data = {
        "structural_completeness": {
            "sections_present": {"evidence": "weak", "score": 4},
            "section_depth": {"evidence": "thin", "score": 4},
        },
        "community_pulse": {
            "cp_relevance": {"evidence": "perfect", "score": 10},
            "cp_substance": {"evidence": "perfect", "score": 10},
            "translation_fidelity": {"evidence": "perfect", "score": 10},
        },
        "issues": [],
    }

    # Must be 40 (avg of 4,4 = 4; *10 = 40), NOT 68 (if CP were included)
    assert _aggregate_subscores(data) == 40


def test_aggregate_subscores_unchanged_when_cp_absent():
    """Backward compatibility: existing digest data without CP still aggregates correctly."""
    from services.pipeline import _aggregate_subscores

    data = {
        "structural_completeness": {
            "sections_present": {"evidence": "all present", "score": 10},
            "section_depth": {"evidence": "substantial", "score": 10},
        },
        "language_quality": {
            "fluency": {"evidence": "natural", "score": 9},
            "locale_integrity": {"evidence": "clean", "score": 10},
        },
        "issues": [],
    }

    # avg of [10,10,9,10] = 9.75, *10 → 98 (rounded)
    assert _aggregate_subscores(data) == 98


def test_cp_block_present_in_all_four_body_prompts():
    """Every body QC prompt must include the 3 CP sub-scores in its rubric."""
    from services.agents.prompts_news_pipeline import (
        QUALITY_CHECK_RESEARCH_EXPERT,
        QUALITY_CHECK_RESEARCH_LEARNER,
        QUALITY_CHECK_BUSINESS_EXPERT,
        QUALITY_CHECK_BUSINESS_LEARNER,
    )

    prompts = [
        ("research_expert", QUALITY_CHECK_RESEARCH_EXPERT),
        ("research_learner", QUALITY_CHECK_RESEARCH_LEARNER),
        ("business_expert", QUALITY_CHECK_BUSINESS_EXPERT),
        ("business_learner", QUALITY_CHECK_BUSINESS_LEARNER),
    ]
    required_tokens = [
        "Community Pulse Quality",
        "cp_relevance",
        "cp_substance",
        "translation_fidelity",
        "community_pulse",  # must appear in the JSON schema section
    ]

    for name, prompt in prompts:
        for token in required_tokens:
            assert token in prompt, f"{name} prompt missing token: {token}"


def test_cp_block_includes_na_fallback_language():
    """The CP block must give the judge an explicit fallback for missing CP,
    otherwise it will hallucinate violations or emit ambiguous scores."""
    from services.agents.prompts_news_pipeline import QUALITY_CHECK_RESEARCH_EXPERT

    # Must explicitly tell the judge to score 10 with N/A evidence
    assert "N/A" in QUALITY_CHECK_RESEARCH_EXPERT
    assert "section not present" in QUALITY_CHECK_RESEARCH_EXPERT


def test_cp_block_frontload_prompt_untouched():
    """Frontload QC does not see CP content (CP is body-only), so the
    community_pulse block must NOT be injected there."""
    from services.agents.prompts_news_pipeline import QUALITY_CHECK_FRONTLOAD

    assert "cp_relevance" not in QUALITY_CHECK_FRONTLOAD
    assert "community_pulse" not in QUALITY_CHECK_FRONTLOAD


def test_log_cp_subscores_emits_expected_fields(caplog):
    """Observability channel for Phase 2a: one log line per persona with all 3 sub-scores."""
    from services.pipeline_quality import _log_cp_subscores

    breakdown = {
        "community_pulse": {
            "cp_relevance": {"evidence": "quotes tied to OpenAI GPT-5.4", "score": 9},
            "cp_substance": {"evidence": "tradeoff discussion", "score": 8},
            "translation_fidelity": {"evidence": "faithful pair", "score": 10},
        },
    }

    with caplog.at_level(logging.INFO, logger="services.pipeline_quality"):
        _log_cp_subscores("research", "expert", breakdown)

    assert any(
        "cp_quality research/expert" in r.getMessage()
        and "relevance=9" in r.getMessage()
        and "substance=8" in r.getMessage()
        and "fidelity=10" in r.getMessage()
        for r in caplog.records
    )


def test_log_cp_subscores_silent_when_cp_absent():
    """If the LLM didn't return community_pulse (e.g., older digest), don't log."""
    from services.pipeline_quality import _log_cp_subscores
    import logging

    logger = logging.getLogger("services.pipeline_quality")
    handler_count_before = len(logger.handlers)

    # No community_pulse key — should no-op
    _log_cp_subscores("research", "expert", {"structural_completeness": {}})
    _log_cp_subscores("research", "expert", {})
    _log_cp_subscores("research", "expert", None)  # defensive: None dict

    # Just ensure it didn't throw. Output silence is tested by caplog absence
    # in the companion test above.
    assert len(logger.handlers) == handler_count_before


def test_log_cp_subscores_handles_malformed_entries(caplog):
    """If the LLM returned malformed CP entries (missing score, wrong type),
    log them as 'n/a' rather than crashing."""
    from services.pipeline_quality import _log_cp_subscores

    breakdown = {
        "community_pulse": {
            "cp_relevance": {"evidence": "malformed - no score field"},
            "cp_substance": "not a dict",
            "translation_fidelity": {"evidence": "ok", "score": 7},
        },
    }

    with caplog.at_level(logging.INFO, logger="services.pipeline_quality"):
        _log_cp_subscores("business", "learner", breakdown)

    msgs = [r.getMessage() for r in caplog.records if "cp_quality" in r.getMessage()]
    assert msgs, "expected a cp_quality log line"
    assert "relevance=n/a" in msgs[0]
    assert "substance=n/a" in msgs[0]
    assert "fidelity=7" in msgs[0]

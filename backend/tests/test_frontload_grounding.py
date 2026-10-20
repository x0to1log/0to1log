"""FRONTLOAD-GROUND-01 Phase 1: detect EN frontload claims missing from sources."""
from unittest.mock import AsyncMock, patch

import pytest

from services.frontload_grounding import check_frontload_grounding, frontload_claims


def _statuses(report: dict) -> dict[str, str]:
    return {
        item["claim"]: status
        for status in ("unsupported", "weak", "supported")
        for item in report[status]
    }


def test_number_missing_from_sources_is_unsupported():
    # 09-28 research: "63x lower scoring cost" had no source sentence.
    frontload = {"headline": "New judge model", "excerpt": "Cuts evaluation with 63x lower scoring cost."}
    source = "The paper reports a judge model that lowers scoring cost on long reasoning traces."
    assert _statuses(check_frontload_grounding(frontload, source))["63x"] == "unsupported"


def test_number_present_only_in_an_unrelated_sentence_is_weak():
    # 10-15 business: "cached inputs 95% off" — the source's 95% meant something else.
    frontload = {"excerpt": "Pricing drops with cached inputs 95% off."}
    source = (
        "A survey found 95% of enterprises plan to adopt agents next year. "
        "The new tier lowers prices for repeated prompts."
    )
    assert _statuses(check_frontload_grounding(frontload, source))["95%"] == "weak"


def test_number_stated_by_the_source_in_another_unit_form_is_supported():
    frontload = {"headline": "Lab commits $500 billion to data centers"}
    source = "The company said it will spend $500B on new data centers through 2030."
    assert _statuses(check_frontload_grounding(frontload, source))["500 billion"] == "supported"


def test_names_are_checked_case_insensitively_and_versions_match_without_v():
    frontload = {
        "headline": "OpenAI ships v0.22.3 of its SDK",
        "focus_items": ["AISI gets early access"],
    }
    source = "openai released version 0.22.3 of the agents sdk on Tuesday."
    statuses = _statuses(check_frontload_grounding(frontload, source))
    assert statuses["OpenAI"] == "supported"
    assert statuses["v0.22.3"] == "supported"
    assert statuses["AISI"] == "unsupported"


def test_only_distinctive_en_tokens_are_checked():
    frontload = {
        "headline": "Meta releases Muse Wonder and Gemini 4 gets 3 new modes",
        "headline_ko": "메타, 5,000억 달러 투자",
        "excerpt_ko": "KISA 발표",
    }
    claims = {claim.text for claim in frontload_claims(frontload)}
    assert "Gemini 4" in claims          # Capitalized phrase with a number
    assert "Muse Wonder" not in claims   # plain Title Case phrase: rarely verbatim
    assert "3" not in claims             # bare short integer
    assert "KISA" not in claims          # KO fields are not checked
    assert not any("5,000" in c for c in claims)


def test_hyphen_variants_in_sources_still_match():
    frontload = {"headline": "GPT-6 Luna pricing", "excerpt": "Gemini-4 Argon follows."}
    source = "GPT‑6 Luna costs less than Gemini 4 Argon, the previous model."
    statuses = _statuses(check_frontload_grounding(frontload, source))
    assert statuses["GPT-6 Luna"] == "supported"
    assert statuses["GPT-6"] == "supported"
    assert statuses["Gemini-4"] == "supported"


def test_single_word_model_names_are_checked():
    frontload = {"headline": "Qwen4 beats o4-mini on coding"}
    source = "Alibaba's new Qwen3 model edges out o4-mini on coding benchmarks."
    statuses = _statuses(check_frontload_grounding(frontload, source))
    assert statuses["Qwen4"] == "unsupported"
    assert statuses["o4-mini"] == "supported"


@pytest.mark.asyncio
async def test_grounding_is_logged_as_a_detection_only_stage():
    from services.pipeline_digest import _log_frontload_grounding

    with patch("services.pipeline_digest._log_stage", new_callable=AsyncMock) as log_mock:
        await _log_frontload_grounding(
            None, "run-1", "business",
            {"excerpt": "Cuts cost with 63x lower scoring cost."},
            "No numbers here.",
        )

    args, kwargs = log_mock.await_args
    assert args[2] == "digest:business:frontload_grounding"
    assert args[3] == "success"
    assert kwargs["debug_meta"]["unsupported"] == [{"claim": "63x", "kind": "number"}]


@pytest.mark.asyncio
async def test_grounding_failure_never_blocks_the_digest():
    from services.pipeline_digest import _log_frontload_grounding

    with patch("services.frontload_grounding.frontload_claims", side_effect=RuntimeError("boom")), \
         patch("services.pipeline_digest._log_stage", new_callable=AsyncMock) as log_mock:
        await _log_frontload_grounding(None, "run-1", "business", {"headline": "x"}, "y")

    log_mock.assert_not_awaited()

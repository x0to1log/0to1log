import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.news_pipeline import ClassifiedGroup, GroupedItem, PersonaOutput


def _mock_openai_response(payload: dict, tokens: int = 400):
    response = MagicMock()
    response.choices[0].message.content = json.dumps(payload)
    response.usage = MagicMock()
    response.usage.prompt_tokens = 1000
    response.usage.completion_tokens = tokens
    response.usage.total_tokens = 1000 + tokens
    return response


def _sample_group() -> list[ClassifiedGroup]:
    return [
        ClassifiedGroup(
            group_title="Thinking Machines secures Nvidia compute deal",
            items=[GroupedItem(url="https://example.com/story", title="Thinking Machines secures Nvidia compute deal")],
            category="business",
            subcategory="industry",
            reason="[LEAD] Major",
        )
    ]


def test_aggregate_subscores_handles_frontload_v11_schema():
    """NQ-37: frontload prompt now emits the same nested-subscore shape as
    the 4 body prompts. _aggregate_subscores must average across all 10
    sub-scores (3+2+2+3) and normalize to 0-100, without falling back to
    legacy data["score"]."""
    from services.pipeline import _aggregate_subscores

    # Representative v11 frontload LLM output — 10 sub-scores, no total
    data = {
        "factuality": {
            "number_grounding": {"evidence": "$510M matches body", "score": 10},
            "entity_grounding": {"evidence": "Cerebras, OpenAI, AWS all body-consistent", "score": 10},
            "claim_grounding":  {"evidence": "'files for IPO' is factual", "score": 10},
        },
        "calibration": {
            "claim_strength":      {"evidence": "'capital shift' is mildly editorial", "score": 8},
            "framing_calibration": {"evidence": "no forward-looking verbs", "score": 10},
        },
        "clarity": {
            "headline_specificity":        {"evidence": "names Cerebras + IPO + OpenAI+AWS", "score": 10},
            "focus_items_informativeness": {"evidence": "3 distinct bullets, no redundancy", "score": 9},
        },
        "locale_alignment": {
            "fact_parity":        {"evidence": "all numbers and entities paired", "score": 10},
            "entity_parity":      {"evidence": "세레브라스 = Cerebras transliteration", "score": 10},
            "phrase_naturalness": {"evidence": "KO reads natively", "score": 9},
        },
        "issues": [],
    }

    score = _aggregate_subscores(data)
    # avg of [10,10,10,8,10,10,9,10,10,9] = 9.6; *10 → 96
    assert score == 96

    # Legacy fallback must NOT kick in when sub-scores present
    assert "score" not in data  # legacy flat score key absent
    # With `score` field added (defensive), aggregator still prefers sub-scores
    data_with_legacy = {**data, "score": 50}
    assert _aggregate_subscores(data_with_legacy) == 96


def test_build_quality_payloads_include_ko_and_frontload_fields():
    from services.pipeline import (
        _build_body_quality_payload,
        _build_frontload_quality_payload,
    )

    body_payload = _build_body_quality_payload(
        "expert",
        PersonaOutput(
            en="## One-Line Summary\nEnglish body",
            ko="## 한 줄 요약\n한국어 본문",
        ),
    )
    frontload_payload = _build_frontload_quality_payload(
        {
            "headline": "English headline",
            "headline_ko": "한국어 제목",
            "excerpt": "English excerpt",
            "excerpt_ko": "한국어 요약",
            "focus_items": ["English point"],
            "focus_items_ko": ["한국어 포인트"],
        }
    )

    assert "=== EN ===" in body_payload
    assert "=== KO ===" in body_payload
    assert "한국어 본문" in body_payload
    assert "English headline" in frontload_payload
    assert "한국어 제목" in frontload_payload
    assert "English point" in frontload_payload
    assert "한국어 포인트" in frontload_payload


def test_normalize_scope_handles_llm_variants():
    from services.pipeline import _normalize_scope

    assert _normalize_scope("frontload", "en") == "frontload"
    assert _normalize_scope("expert_body|ko|en", "en") == "expert_body"
    assert _normalize_scope("Frontload", "en") == "frontload"
    assert _normalize_scope("misc|frontload", "en") == "frontload"
    assert _normalize_scope(" expert_body | en ", "ko") == "expert_body"
    assert _normalize_scope("", "learner_body") == "learner_body"
    assert _normalize_scope(None, "en") == "en"
    assert _normalize_scope("   ", "en") == "en"
    assert _normalize_scope("unknown_scope", "en") == "unknown_scope"


def test_issue_penalty_cap_activates_with_piped_scope():
    """LLM may return 'frontload|en|ko' — cap must still activate."""
    from services.pipeline import _apply_issue_penalties_and_caps, _extract_structured_issues

    raw_issues = [
        {
            "severity": "major",
            "scope": "frontload|en|ko",
            "category": "overclaim",
            "message": "Headline overstates competitive impact",
        }
    ]
    normalized = _extract_structured_issues(raw_issues, default_scope="en")
    assert normalized[0]["scope"] == "frontload"

    final_score, penalty, caps = _apply_issue_penalties_and_caps(
        base_score=97,
        issues=normalized,
    )
    assert penalty == 5
    assert "frontload_overclaim_cap_89" in caps
    assert final_score == 89


def test_issue_penalty_and_caps_are_deterministic():
    from services.pipeline import _apply_issue_penalties_and_caps

    final_score, penalty, caps = _apply_issue_penalties_and_caps(
        base_score=97,
        issues=[
            {
                "severity": "major",
                "scope": "frontload",
                "category": "overclaim",
                "message": "Headline overstates the competitive impact",
            },
            {
                "severity": "minor",
                "scope": "learner_body",
                "category": "accessibility",
                "message": "One acronym is unexplained",
            },
        ],
    )

    assert penalty == 7
    assert "frontload_overclaim_cap_89" in caps
    assert final_score == 89


@pytest.mark.asyncio
async def test_check_digest_quality_uses_ko_and_frontload_and_applies_cap():
    from services.pipeline import _check_digest_quality

    personas = {
        "expert": PersonaOutput(
            en="## One-Line Summary\nEnglish expert body [1](https://example.com/story)\n\n## Industry & Biz\n\n### Thinking Machines deal\n\nFirst paragraph [1](https://example.com/story)\n\nSecond paragraph [1](https://example.com/story)\n\nThird paragraph [1](https://example.com/story)\n",
            ko="## 한 줄 요약\n한국어 전문가 본문 [1](https://example.com/story)\n\n## Industry & Biz\n\n### Thinking Machines 딜\n\n첫 문단 [1](https://example.com/story)\n\n둘째 문단 [1](https://example.com/story)\n\n셋째 문단 [1](https://example.com/story)\n",
        ),
        "learner": PersonaOutput(
            en="## One-Line Summary\nEnglish learner body [1](https://example.com/story)\n\n## What This Means for You\n\n### Why it matters\n\nFirst paragraph [1](https://example.com/story)\n\nSecond paragraph [1](https://example.com/story)\n\nThird paragraph [1](https://example.com/story)\n",
            ko="## 한 줄 요약\n한국어 학습자 본문 [1](https://example.com/story)\n\n## What This Means for You\n\n### 왜 중요한가\n\n첫 문단 [1](https://example.com/story)\n\n둘째 문단 [1](https://example.com/story)\n\n셋째 문단 [1](https://example.com/story)\n",
        ),
    }
    frontload = {
        "headline": "Nvidia wins the AI infrastructure war with a Thinking Machines compute deal",
        "headline_ko": "엔비디아가 Thinking Machines 딜로 AI 인프라 전쟁 승리",
        "excerpt": "This deal proves Nvidia now controls AI distribution end to end.",
        "excerpt_ko": "이 딜은 엔비디아가 AI 유통을 끝까지 장악했음을 증명한다.",
        "focus_items": ["Thinking Machines signs 1GW deal", "Compute concentration deepens", "Watch financing and supply control"],
        "focus_items_ko": ["Thinking Machines, 1GW 계약 체결", "컴퓨트 집중 심화", "자금·공급 통제 주목"],
    }

    captured_user_prompts: list[str] = []
    responses = [
        _mock_openai_response(
            {
                "score": 95,
                "subscores": {"sections": 24, "sources": 24, "analysis": 24, "language": 23},
                "issues": [],
            }
        ),
        _mock_openai_response(
            {
                "score": 94,
                "subscores": {"sections": 24, "accessibility": 24, "actionability": 23, "language": 23},
                "issues": [],
            }
        ),
        _mock_openai_response(
            {
                "score": 96,
                "subscores": {"factuality": 19, "calibration": 19, "clarity": 19, "locale_alignment": 19},
                "issues": [
                    {
                        "severity": "major",
                        "scope": "frontload",
                        "category": "overclaim",
                        "message": "Headline and excerpt overstate the competitive conclusion beyond source support",
                    }
                ],
            }
        ),
    ]

    async def _capture_create(*args, **kwargs):
        captured_user_prompts.append(kwargs["messages"][1]["content"])
        return responses.pop(0)

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=_capture_create)

    with patch("services.pipeline_quality.get_openai_client", return_value=mock_client), \
         patch("services.pipeline_quality._log_stage", new_callable=AsyncMock), \
         patch("services.pipeline_quality.settings") as mock_settings:
        mock_settings.openai_model_reasoning = "gpt-5-mini"

        result = await _check_digest_quality(
            personas=personas,
            digest_type="business",
            classified=_sample_group(),
            community_summary_map={},
            supabase=MagicMock(),
            run_id="run-1",
            cumulative_usage={},
            frontload=frontload,
        )

    assert result["score"] == 89
    assert result["issue_penalty"] == 5
    assert "frontload_overclaim_cap_89" in result["quality_caps_applied"]
    assert any("한국어 전문가 본문" in prompt for prompt in captured_user_prompts[:2])
    assert "AI infrastructure war" in captured_user_prompts[2]
    assert "엔비디아가 Thinking Machines 딜로 AI 인프라 전쟁 승리" in captured_user_prompts[2]


@pytest.mark.asyncio
async def test_check_digest_quality_returns_per_call_breakdowns_for_admin_drill_down():
    """_check_digest_quality must return expert_breakdown/learner_breakdown/
    frontload_breakdown — the nested v11 sub-score evidence structure that
    admin UI renders. These are produced internally (pipeline_quality.py:539-541)
    but tested explicitly here to guard against accidental removal. (NQ-34)"""
    from services.pipeline import _check_digest_quality

    personas = {
        "expert": PersonaOutput(
            en="## One-Line Summary\nEnglish expert body [1](https://example.com/story)\n\n## Industry & Biz\n\n### Thinking Machines deal\n\nFirst paragraph [1](https://example.com/story)\n\nSecond paragraph [1](https://example.com/story)\n\nThird paragraph [1](https://example.com/story)\n",
            ko="## 한 줄 요약\n한국어 전문가 본문 [1](https://example.com/story)\n\n## Industry & Biz\n\n### Thinking Machines 딜\n\n첫 문단 [1](https://example.com/story)\n\n둘째 문단 [1](https://example.com/story)\n\n셋째 문단 [1](https://example.com/story)\n",
        ),
        "learner": PersonaOutput(
            en="## One-Line Summary\nEnglish learner body [1](https://example.com/story)\n\n## What This Means for You\n\n### Why it matters\n\nFirst paragraph [1](https://example.com/story)\n\nSecond paragraph [1](https://example.com/story)\n\nThird paragraph [1](https://example.com/story)\n",
            ko="## 한 줄 요약\n한국어 학습자 본문 [1](https://example.com/story)\n\n## What This Means for You\n\n### 왜 중요한가\n\n첫 문단 [1](https://example.com/story)\n\n둘째 문단 [1](https://example.com/story)\n\n셋째 문단 [1](https://example.com/story)\n",
        ),
    }
    frontload = {
        "headline": "Nvidia signs Thinking Machines compute deal",
        "headline_ko": "엔비디아, Thinking Machines 컴퓨트 딜 체결",
        "excerpt": "Deal lands with industry implications.",
        "excerpt_ko": "업계 영향과 함께 체결된 딜.",
        "focus_items": ["Deal signed", "Compute expands", "Watch supply"],
        "focus_items_ko": ["계약 체결", "컴퓨트 확장", "공급 주목"],
    }

    # Representative v11 nested sub-score payloads (structure matches what
    # pipeline_quality.py:539-541 extracts into the *_breakdown fields).
    expert_payload = {
        "structural_completeness": {
            "sections_present": {"evidence": "All required sections present", "score": 10},
            "paragraph_depth":   {"evidence": "3 paragraphs per section", "score": 9},
            "subheading_quality": {"evidence": "Subheadings are concrete", "score": 10},
        },
        "source_quality": {
            "citation_density": {"evidence": "Each paragraph cited", "score": 10},
            "source_diversity": {"evidence": "Single source OK here", "score": 8},
        },
        "issues": [],
    }
    learner_payload = {
        "structural_completeness": {
            "sections_present": {"evidence": "Required sections present", "score": 10},
            "paragraph_depth":   {"evidence": "Adequate paragraph depth", "score": 9},
        },
        "accessibility": {
            "jargon_handling": {"evidence": "Terms explained inline", "score": 9},
        },
        "issues": [],
    }
    frontload_payload = {
        "factuality": {
            "number_grounding": {"evidence": "No numbers in headline", "score": 10},
            "entity_grounding": {"evidence": "Entities body-consistent", "score": 10},
            "claim_grounding":  {"evidence": "Deal claim factual", "score": 10},
        },
        "calibration": {
            "claim_strength":      {"evidence": "Neutral framing", "score": 10},
            "framing_calibration": {"evidence": "No forward-looking verbs", "score": 10},
        },
        "clarity": {
            "headline_specificity":        {"evidence": "Names both parties", "score": 10},
            "focus_items_informativeness": {"evidence": "Distinct bullets", "score": 9},
        },
        "locale_alignment": {
            "fact_parity":        {"evidence": "EN/KO facts parity", "score": 10},
            "entity_parity":      {"evidence": "Entity transliteration aligned", "score": 10},
            "phrase_naturalness": {"evidence": "KO reads natively", "score": 9},
        },
        "issues": [],
    }

    responses = [
        _mock_openai_response(expert_payload),
        _mock_openai_response(learner_payload),
        _mock_openai_response(frontload_payload),
    ]

    async def _create(*args, **kwargs):
        return responses.pop(0)

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=_create)

    with patch("services.pipeline_quality.get_openai_client", return_value=mock_client), \
         patch("services.pipeline_quality._log_stage", new_callable=AsyncMock), \
         patch("services.pipeline_quality.settings") as mock_settings:
        mock_settings.openai_model_reasoning = "gpt-5-mini"

        result = await _check_digest_quality(
            personas=personas,
            digest_type="business",
            classified=_sample_group(),
            community_summary_map={},
            supabase=MagicMock(),
            run_id="run-drill-down",
            cumulative_usage={},
            frontload=frontload,
        )

    # The 3 breakdown keys are the evidence trail admin UI renders (NQ-34).
    assert isinstance(result.get("expert_breakdown"), dict)
    assert isinstance(result.get("learner_breakdown"), dict)
    assert isinstance(result.get("frontload_breakdown"), dict)
    assert result["expert_breakdown"], "expert_breakdown must be non-empty"
    assert result["learner_breakdown"], "learner_breakdown must be non-empty"
    assert result["frontload_breakdown"], "frontload_breakdown must be non-empty"

    # Verify nested sub-score shape preserved — admin UI reads evidence strings.
    expert_bd = result["expert_breakdown"]
    assert "structural_completeness" in expert_bd
    assert "sections_present" in expert_bd["structural_completeness"]
    assert expert_bd["structural_completeness"]["sections_present"]["evidence"]

    frontload_bd = result["frontload_breakdown"]
    assert "locale_alignment" in frontload_bd
    assert frontload_bd["locale_alignment"]["fact_parity"]["evidence"]


# ---------------------------------------------------------------------------
# Phase 2 — URL Strict Allowlist Validation
# ---------------------------------------------------------------------------

class TestValidateCitationUrls:
    """Verify URL strict allowlist validation against fact_pack.news_items."""

    def test_all_citations_in_fact_pack_passes(self):
        from services.pipeline import validate_citation_urls
        body = "Some content. [1](https://example.com/a)\n\nMore. [2](https://example.com/b)"
        fact_pack = {"news_items": [
            {"url": "https://example.com/a", "title": "A"},
            {"url": "https://example.com/b", "title": "B"},
        ]}
        result = validate_citation_urls(body, fact_pack)
        assert result["valid"] is True
        assert result["unknown_urls"] == []

    def test_unknown_url_fails(self):
        from services.pipeline import validate_citation_urls
        body = "Cited [1](https://hallucinated.example.com/fake)."
        fact_pack = {"news_items": [{"url": "https://example.com/real", "title": "R"}]}
        result = validate_citation_urls(body, fact_pack)
        assert result["valid"] is False
        assert "https://hallucinated.example.com/fake" in result["unknown_urls"]

    def test_zero_citations_passes(self):
        """Sections like One-Line Summary may have no citations — must pass."""
        from services.pipeline import validate_citation_urls
        body = "Just a summary, no citations.\n\n## Section\n\nMore prose."
        fact_pack = {"news_items": [{"url": "https://example.com/a", "title": "A"}]}
        result = validate_citation_urls(body, fact_pack)
        assert result["valid"] is True
        assert result["unknown_urls"] == []
        assert result["citation_count"] == 0

    def test_url_normalization_strips_tracking_params(self):
        """utm_*, fbclid, ref params should normalize away before comparing."""
        from services.pipeline import validate_citation_urls
        body = "Cited [1](https://example.com/a?utm_source=twitter&utm_medium=social)."
        fact_pack = {"news_items": [{"url": "https://example.com/a", "title": "A"}]}
        result = validate_citation_urls(body, fact_pack)
        assert result["valid"] is True

    def test_url_normalization_strips_trailing_slash(self):
        from services.pipeline import validate_citation_urls
        body = "Cited [1](https://example.com/a/)."
        fact_pack = {"news_items": [{"url": "https://example.com/a", "title": "A"}]}
        result = validate_citation_urls(body, fact_pack)
        assert result["valid"] is True

    def test_url_normalization_strips_fragment(self):
        from services.pipeline import validate_citation_urls
        body = "Cited [1](https://example.com/a#section-2)."
        fact_pack = {"news_items": [{"url": "https://example.com/a", "title": "A"}]}
        result = validate_citation_urls(body, fact_pack)
        assert result["valid"] is True

    def test_duplicate_citations_deduped(self):
        """Same URL cited multiple times = 1 unique URL to validate."""
        from services.pipeline import validate_citation_urls
        body = "First [1](https://example.com/a). Second [1](https://example.com/a)."
        fact_pack = {"news_items": [{"url": "https://example.com/a", "title": "A"}]}
        result = validate_citation_urls(body, fact_pack)
        assert result["valid"] is True
        assert result["citation_count"] == 1

    def test_empty_fact_pack_with_citations_fails(self):
        from services.pipeline import validate_citation_urls
        body = "Cited [1](https://example.com/a)."
        fact_pack = {"news_items": []}
        result = validate_citation_urls(body, fact_pack)
        assert result["valid"] is False
        assert "https://example.com/a" in result["unknown_urls"]

    def test_missing_news_items_field_treated_as_empty(self):
        from services.pipeline import validate_citation_urls
        body = "Cited [1](https://example.com/a)."
        fact_pack = {}  # no news_items key
        result = validate_citation_urls(body, fact_pack)
        assert result["valid"] is False


@pytest.mark.asyncio
async def test_check_digest_quality_url_validation_failure_marks_ineligible():
    """Integration: hallucinated URL in body forces auto_publish_eligible=False via quality_meta."""
    from services.pipeline import _check_digest_quality

    BAD_URL = "https://hallucinated.example.com/fake"
    GOOD_URL = "https://example.com/story"

    personas = {
        "expert": PersonaOutput(
            en=(
                "## One-Line Summary\nEnglish expert body [1](" + GOOD_URL + ")\n\n"
                "## Industry & Biz\n\n"
                "### Thinking Machines deal\n\n"
                "First paragraph [1](" + BAD_URL + ")\n\n"
                "Second paragraph [1](" + GOOD_URL + ")\n\n"
                "Third paragraph [1](" + GOOD_URL + ")\n"
            ),
            ko=(
                "## 한 줄 요약\n한국어 전문가 본문 [1](" + GOOD_URL + ")\n\n"
                "## Industry & Biz\n\n"
                "### Thinking Machines 딜\n\n"
                "첫 문단 [1](" + GOOD_URL + ")\n\n"
                "둘째 문단 [1](" + GOOD_URL + ")\n\n"
                "셋째 문단 [1](" + GOOD_URL + ")\n"
            ),
        ),
        "learner": PersonaOutput(
            en=(
                "## One-Line Summary\nEnglish learner body [1](" + GOOD_URL + ")\n\n"
                "## What This Means for You\n\n"
                "### Why it matters\n\n"
                "First paragraph [1](" + GOOD_URL + ")\n\n"
                "Second paragraph [1](" + GOOD_URL + ")\n\n"
                "Third paragraph [1](" + GOOD_URL + ")\n"
            ),
            ko=(
                "## 한 줄 요약\n한국어 학습자 본문 [1](" + GOOD_URL + ")\n\n"
                "## What This Means for You\n\n"
                "### 왜 중요한가\n\n"
                "첫 문단 [1](" + GOOD_URL + ")\n\n"
                "둘째 문단 [1](" + GOOD_URL + ")\n\n"
                "셋째 문단 [1](" + GOOD_URL + ")\n"
            ),
        ),
    }
    frontload = {
        "headline": "Nvidia wins",
        "headline_ko": "엔비디아 승리",
        "excerpt": "Nvidia infrastructure dominance.",
        "excerpt_ko": "엔비디아 인프라 지배.",
        "focus_items": ["Deal signed"],
        "focus_items_ko": ["계약 체결"],
    }

    # Mock LLM judge call with clean (no-issue) scores so we're testing ONLY URL validation
    responses = [
        _mock_openai_response({"score": 95, "subscores": {}, "issues": []}),
        _mock_openai_response({"score": 94, "subscores": {}, "issues": []}),
        _mock_openai_response({"score": 96, "subscores": {}, "issues": []}),
    ]

    async def _create(*args, **kwargs):
        return responses.pop(0)

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=_create)

    with patch("services.pipeline_quality.get_openai_client", return_value=mock_client), \
         patch("services.pipeline_quality._log_stage", new_callable=AsyncMock), \
         patch("services.pipeline_quality.settings") as mock_settings:
        mock_settings.openai_model_reasoning = "gpt-5-mini"

        result = await _check_digest_quality(
            personas=personas,
            digest_type="business",
            classified=_sample_group(),  # has primary_url = GOOD_URL
            community_summary_map={},
            supabase=MagicMock(),
            run_id="run-url-val",
            cumulative_usage={},
            frontload=frontload,
        )

    # URL validation flags
    assert result["url_validation_failed"] is True
    assert result["auto_publish_eligible"] is False
    failures = result["url_validation_failures"]
    assert len(failures) >= 1
    # Check that BAD_URL is in at least one failure's unknown_urls
    all_unknown = [u for f in failures for u in f["unknown_urls"]]
    assert BAD_URL in all_unknown
    # Only the expert.en content has the bad URL, so exactly one failure entry expected
    expert_en_failures = [f for f in failures if f["persona"] == "expert" and f["locale"] == "en"]
    assert len(expert_en_failures) == 1
    assert BAD_URL in expert_en_failures[0]["unknown_urls"]


@pytest.mark.asyncio
async def test_check_digest_quality_url_validation_passes_when_all_cited():
    """Happy path: all citations resolve to fact_pack URLs → url_validation_failed=False."""
    from services.pipeline import _check_digest_quality

    GOOD_URL = "https://example.com/story"

    personas = {
        "expert": PersonaOutput(
            en=(
                "## One-Line Summary\nExpert body [1](" + GOOD_URL + ")\n\n"
                "### Deal\n\nFirst [1](" + GOOD_URL + ")\n\nSecond [1](" + GOOD_URL + ")\n\nThird [1](" + GOOD_URL + ")\n"
            ),
            ko=(
                "## 한 줄 요약\n본문 [1](" + GOOD_URL + ")\n\n"
                "### 딜\n\n첫 [1](" + GOOD_URL + ")\n\n둘 [1](" + GOOD_URL + ")\n\n셋 [1](" + GOOD_URL + ")\n"
            ),
        ),
    }

    responses = [
        _mock_openai_response({"score": 95, "subscores": {}, "issues": []}),
        _mock_openai_response({"score": 96, "subscores": {}, "issues": []}),
    ]

    async def _create(*args, **kwargs):
        return responses.pop(0)

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=_create)

    with patch("services.pipeline_quality.get_openai_client", return_value=mock_client), \
         patch("services.pipeline_quality._log_stage", new_callable=AsyncMock), \
         patch("services.pipeline_quality.settings") as mock_settings:
        mock_settings.openai_model_reasoning = "gpt-5-mini"

        result = await _check_digest_quality(
            personas=personas,
            digest_type="business",
            classified=_sample_group(),
            community_summary_map={},
            supabase=MagicMock(),
            run_id="run-url-ok",
            cumulative_usage={},
            frontload=None,
        )

    assert result["url_validation_failed"] is False
    assert "auto_publish_eligible" not in result or result.get("auto_publish_eligible") is not False


@pytest.mark.asyncio
async def test_check_digest_quality_allowlist_includes_all_group_items_not_just_primary():
    """Regression guard (2026-04-16 production bug):
    URL validator must treat EVERY item URL in a ClassifiedGroup as allowed,
    not just items[0] (primary). Citing a non-primary item legitimately
    must NOT trigger url_validation_failed.
    """
    from services.pipeline import _check_digest_quality

    PRIMARY = "https://primary.example.com/a"
    SECONDARY = "https://secondary.example.com/b"
    TERTIARY = "https://tertiary.example.com/c"

    classified = [
        ClassifiedGroup(
            group_title="Multi-item group",
            items=[
                GroupedItem(url=PRIMARY, title="Primary"),
                GroupedItem(url=SECONDARY, title="Secondary"),
                GroupedItem(url=TERTIARY, title="Tertiary"),
            ],
            category="business",
            subcategory="industry",
            reason="[LEAD]",
        )
    ]

    # Body cites the SECONDARY URL (not the primary) — this is legitimate
    # because the writer was given all three items.
    personas = {
        "expert": PersonaOutput(
            en=f"## One-Line Summary\nExpert body [1]({SECONDARY})\n\n### Deal\n\nPara [1]({TERTIARY})\n",
            ko=f"## 한 줄 요약\n본문 [1]({SECONDARY})\n\n### 딜\n\n단락 [1]({TERTIARY})\n",
        ),
    }

    responses = [
        _mock_openai_response({"score": 95, "subscores": {}, "issues": []}),
        _mock_openai_response({"score": 96, "subscores": {}, "issues": []}),
    ]

    async def _create(*args, **kwargs):
        return responses.pop(0)

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=_create)

    with patch("services.pipeline_quality.get_openai_client", return_value=mock_client), \
         patch("services.pipeline_quality._log_stage", new_callable=AsyncMock), \
         patch("services.pipeline_quality.settings") as mock_settings:
        mock_settings.openai_model_reasoning = "gpt-5-mini"

        result = await _check_digest_quality(
            personas=personas,
            digest_type="business",
            classified=classified,
            community_summary_map={},
            supabase=MagicMock(),
            run_id="run-allowlist",
            cumulative_usage={},
            frontload=None,
        )

    assert result["url_validation_failed"] is False, (
        f"Non-primary group items should be in allowlist, but got failures: "
        f"{result.get('url_validation_failures')}"
    )


@pytest.mark.asyncio
async def test_check_digest_quality_allowlist_includes_enriched_urls():
    """Regression guard (2026-04-16 2nd production verification):
    URLs passed via enriched_map (post-classification enrichment) must be
    in the allowlist. Without this, writers citing legitimate enriched URLs
    trigger url_validation_failed=true, trapping every research digest in draft.
    """
    from services.pipeline import _check_digest_quality

    GROUP_URL = "https://primary.example.com/story"
    ENRICHED_RELATED_URL = "https://related.example.com/analysis"
    ENRICHED_ANCHOR_URL = "https://anchor.example.com/hub"

    classified = [
        ClassifiedGroup(
            group_title="Research with enrichment",
            items=[GroupedItem(url=GROUP_URL, title="Primary")],
            category="research",
            subcategory="papers",
            reason="[LEAD]",
        )
    ]

    # Enrichment adds URLs the writer sees but that don't belong to any ClassifiedGroup
    enriched_map = {
        ENRICHED_ANCHOR_URL: [
            {"url": ENRICHED_RELATED_URL, "title": "Related analysis", "content": "..."},
        ],
    }

    # Body cites the enriched related URL — legitimate, must not trigger failure
    personas = {
        "expert": PersonaOutput(
            en=f"## One-Line Summary\nBody [1]({ENRICHED_RELATED_URL})\n\n### Heading\n\nMore [1]({GROUP_URL})\n",
            ko=f"## 한 줄 요약\n본문 [1]({ENRICHED_RELATED_URL})\n\n### 제목\n\n추가 [1]({GROUP_URL})\n",
        ),
    }

    responses = [
        _mock_openai_response({"score": 95, "subscores": {}, "issues": []}),
        _mock_openai_response({"score": 96, "subscores": {}, "issues": []}),
    ]

    async def _create(*args, **kwargs):
        return responses.pop(0)

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=_create)

    with patch("services.pipeline_quality.get_openai_client", return_value=mock_client), \
         patch("services.pipeline_quality._log_stage", new_callable=AsyncMock), \
         patch("services.pipeline_quality.settings") as mock_settings:
        mock_settings.openai_model_reasoning = "gpt-5-mini"

        result = await _check_digest_quality(
            personas=personas,
            digest_type="research",
            classified=classified,
            community_summary_map={},
            supabase=MagicMock(),
            run_id="run-enriched",
            cumulative_usage={},
            frontload=None,
            enriched_map=enriched_map,
        )

    assert result["url_validation_failed"] is False, (
        f"Enriched URL citations should be in allowlist, but got failures: "
        f"{result.get('url_validation_failures')}"
    )

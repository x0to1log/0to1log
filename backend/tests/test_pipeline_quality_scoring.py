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
            relevance_score=0.9,
            reason="[LEAD] Major",
        )
    ]


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

    with patch("services.pipeline.get_openai_client", return_value=mock_client), \
         patch("services.pipeline._log_stage", new_callable=AsyncMock), \
         patch("services.pipeline.settings") as mock_settings:
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

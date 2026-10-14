"""Auto-publish gate: score threshold AND no blocking quality cap (plan Task 1.7).

The 84 caps were built to sit just under an 85 threshold so a major issue
blocked publishing. A stricter judge scores clean posts below 84 too, so the
block is now an explicit flag instead of a side effect of the score.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import services.pipeline  # noqa: F401 - load re-exports before direct module imports
from services.pipeline_quality import AUTO_PUBLISH_BLOCKING_CAPS, passes_auto_publish_gate


@pytest.fixture
def threshold_70(monkeypatch):
    monkeypatch.setattr("services.pipeline_quality.settings.auto_publish_threshold", 70)


def test_blocking_caps_are_the_major_issue_caps():
    assert AUTO_PUBLISH_BLOCKING_CAPS == {
        "major_source_cap_84", "frontload_overclaim_cap_84", "locale_quality_cap_84",
    }


def test_gate_passes_score_at_threshold_without_caps(threshold_70):
    assert passes_auto_publish_gate(70, []) is True
    assert passes_auto_publish_gate(69, []) is False


def test_gate_blocks_major_issue_cap_even_when_score_clears_threshold(threshold_70):
    assert passes_auto_publish_gate(84, ["major_source_cap_84"]) is False


def test_gate_ignores_non_blocking_caps(threshold_70):
    assert passes_auto_publish_gate(80, ["daily_primary_source_cap_92", "learner_accessibility_cap_92"]) is True


def _draft(slug: str, score: int, caps: list[str]) -> dict:
    return {
        "id": f"id-{slug}", "slug": slug, "quality_score": score, "post_type": "research", "title": slug,
        "fact_pack": {"auto_publish_eligible": True, "quality_caps_applied": caps},
    }


@pytest.mark.asyncio
async def test_promote_drafts_keeps_capped_draft_and_reports_why(threshold_70):
    from services.pipeline_persistence import promote_drafts

    drafts = [_draft("clean", 75, []), _draft("capped", 90, ["major_source_cap_84"])]
    supabase = MagicMock()
    select_chain = supabase.table.return_value.select.return_value
    select_chain.eq.return_value.eq.return_value.in_.return_value.execute.return_value.data = drafts

    with patch("services.pipeline_persistence.get_supabase", return_value=supabase), \
         patch("services.pipeline_persistence._notify_auto_publish", new_callable=AsyncMock), \
         patch("services.pipeline_persistence._send_draft_alert", new_callable=AsyncMock) as alert:
        result = await promote_drafts("2026-10-14")

    assert result["promoted_slugs"] == ["clean"]
    assert result["kept_draft"] == 1
    alert.assert_awaited_once()
    assert alert.await_args.kwargs["blocking_caps"] == ["major_source_cap_84"]

"""Safety contract for scripts/ab_daily_models.py RecorderClient.

The A/B script replays production checkpoints through _generate_digest with a
RecorderClient in place of Supabase. These tests pin the guarantee that it
never forwards writes and fails loudly on any read or delete.
"""
import pytest

from scripts.ab_daily_models import ARMS, ROLES, RecorderClient, quizzes_from_rows


def test_recorder_captures_writes_without_forwarding():
    rec = RecorderClient()
    rec.table("news_posts").upsert({"slug": "a", "quality_score": 80}, on_conflict="slug").execute()
    rec.table("pipeline_logs").insert({"pipeline_type": "quality:research", "status": "success"}).execute()
    rec.table("news_posts").update({"quality_score": 81}).eq("slug", "a").execute()

    assert rec.rows("news_posts") == [{"slug": "a", "quality_score": 80}, {"quality_score": 81}]
    assert rec.rows("pipeline_logs")[0]["status"] == "success"
    assert rec.writes[2]["filters"] == [("slug", "a")]


def test_recorder_read_raises_so_hidden_db_dependencies_surface():
    with pytest.raises(RuntimeError, match="unexpected read from 'handbook_terms'"):
        RecorderClient().table("handbook_terms").select("slug")


def test_recorder_delete_raises():
    with pytest.raises(RuntimeError, match="unexpected delete"):
        RecorderClient().table("news_posts").delete()


def test_every_arm_sets_all_model_roles():
    # A missing role would silently inherit whatever .env says, mixing arms.
    for arm, models in ARMS.items():
        assert set(models) == set(ROLES), arm


def test_quizzes_from_rows_regroups_by_type_persona_and_locale():
    rows = [
        {"post_type": "research", "locale": "en",
         "guide_items": {"quiz_poll_expert": {"q": "en-exp"}, "quiz_poll_learner": {"q": "en-lrn"}, "sources_expert": []}},
        {"post_type": "research", "locale": "ko",
         "guide_items": {"quiz_poll_expert": {"q": "ko-exp"}}},
        {"post_type": "business", "locale": "en", "guide_items": None},
    ]
    assert quizzes_from_rows(rows) == {
        "research": {
            "expert": {"en": {"q": "en-exp"}, "ko": {"q": "ko-exp"}},
            "learner": {"en": {"q": "en-lrn"}},
        },
        "business": {},
    }


def test_expand_date_range_is_inclusive():
    from scripts.ab_daily_models import expand_date_range

    assert expand_date_range("2026-09-29:2026-10-01") == ["2026-09-29", "2026-09-30", "2026-10-01"]
    assert expand_date_range("2026-09-28") == ["2026-09-28"]


def test_threshold_summary_counts_passes_cap_blocks_and_judge_only_blocks():
    from scripts.ab_daily_models import summarize_threshold

    runs = [
        {"date": "d1", "type": "research", "judge": "mini", "score": 91, "caps": [], "major_issues": []},
        {"date": "d1", "type": "research", "judge": "sol", "score": 84, "caps": ["major_source_cap_84"],
         "major_issues": ["63x unsupported"]},
        {"date": "d1", "type": "business", "judge": "mini", "score": 88, "caps": ["daily_primary_source_cap_92"],
         "major_issues": []},
        {"date": "d1", "type": "business", "judge": "sol", "score": 82, "caps": [], "major_issues": []},
    ]
    summary = summarize_threshold(runs, threshold=85, baseline_judge="mini")

    assert summary["by_judge"]["mini"] == {"n": 2, "mean": 89.5, "pass": 2, "cap_blocked": 0}
    assert summary["by_judge"]["sol"] == {"n": 2, "mean": 83.0, "pass": 0, "cap_blocked": 1}
    # Posts the baseline judge would publish but the other judge blocks, with why.
    assert summary["newly_blocked"]["sol"] == [
        {"date": "d1", "type": "research", "baseline": 91, "score": 84,
         "caps": ["major_source_cap_84"], "major_issues": ["63x unsupported"]},
        {"date": "d1", "type": "business", "baseline": 88, "score": 82, "caps": [], "major_issues": []},
    ]


def test_weekly_slugs_match_weekly_digest_naming():
    from scripts.ab_daily_models import weekly_slugs

    assert weekly_slugs("2026-W38") == ("2026-w38-weekly-digest", "2026-w38-weekly-digest-ko")

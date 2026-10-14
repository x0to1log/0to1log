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

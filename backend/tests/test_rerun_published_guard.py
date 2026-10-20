"""RERUN-GUARD-01: a rerun blocked by published posts must not touch the run.

All Supabase access is faked — these tests must never reach the real DB.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from services.pipeline import published_rerun_block_message, rerun_pipeline_stage

BATCH = "2026-10-18"
PUBLISHED_BUSINESS = [{"id": "p1", "slug": f"{BATCH}-business-digest", "post_type": "business", "status": "published"}]


class _RecordingTable:
    def __init__(self, db, name):
        self._db = db
        self._name = name

    def select(self, *args, **kwargs):
        return self

    def update(self, row):
        self._db.writes.append(("update", self._name, row))
        return self

    def delete(self):
        self._db.writes.append(("delete", self._name, None))
        return self

    def eq(self, *args, **kwargs):
        return self

    def neq(self, *args, **kwargs):
        return self

    def execute(self):
        return MagicMock(data=self._db.published if self._name == "news_posts" else [{"id": "run-1"}])


class _RecordingSupabase:
    def __init__(self, published):
        self.published = published
        self.writes = []

    def table(self, name):
        return _RecordingTable(self, name)


def test_block_message_covers_published_scope_but_not_quiz_or_other_category():
    sb = _RecordingSupabase(PUBLISHED_BUSINESS)
    assert "Cannot rerun business" in published_rerun_block_message(sb, BATCH, "write", "business")
    assert "Cannot rerun batch" in published_rerun_block_message(sb, BATCH, "quality", None)
    assert published_rerun_block_message(sb, BATCH, "quiz", "business") is None
    assert published_rerun_block_message(sb, BATCH, "write", "research") is None


@pytest.mark.asyncio
async def test_blocked_rerun_leaves_run_status_and_logs_untouched():
    # Before the fix: the run was claimed as running, the write/quality/save/summary
    # logs were deleted, and only then the guard marked the run failed — erasing a
    # successful run's history and turning the admin health card critical.
    sb = _RecordingSupabase(PUBLISHED_BUSINESS)
    with patch("services.pipeline.get_supabase", return_value=sb):
        result = await rerun_pipeline_stage("run-1", "write", BATCH, category="business")

    assert result.status == "failed"
    assert "Cannot rerun business" in result.errors[0]
    assert sb.writes == []


def test_rerun_endpoint_refuses_published_scope_before_queueing():
    sb = _RecordingSupabase(PUBLISHED_BUSINESS)
    with patch("routers.cron.get_supabase", return_value=sb), \
         patch("routers.cron.rerun_pipeline_stage", new_callable=AsyncMock) as rerun_mock:
        from main import app
        client = TestClient(app)
        with patch("core.security.settings") as mock_settings:
            mock_settings.cron_secret = "test-secret-123"
            response = client.post(
                "/api/cron/pipeline-rerun",
                headers={"x-cron-secret": "test-secret-123"},
                json={"run_id": "run-1", "from_stage": "write", "batch_id": BATCH, "category": "business"},
            )

    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "published_protected"
    rerun_mock.assert_not_awaited()
    assert sb.writes == []


def test_rerun_endpoint_still_queues_quiz_rerun_on_published_posts():
    sb = _RecordingSupabase(PUBLISHED_BUSINESS)
    with patch("routers.cron.get_supabase", return_value=sb), \
         patch("routers.cron.rerun_pipeline_stage", new_callable=AsyncMock) as rerun_mock:
        from main import app
        client = TestClient(app)
        with patch("core.security.settings") as mock_settings:
            mock_settings.cron_secret = "test-secret-123"
            response = client.post(
                "/api/cron/pipeline-rerun",
                headers={"x-cron-secret": "test-secret-123"},
                json={"run_id": "run-1", "from_stage": "quiz", "batch_id": BATCH, "category": "business"},
            )

    assert response.status_code == 202
    rerun_mock.assert_awaited_once()

"""09:00 KST daily recovery: decision table + full-rerun path.

All Supabase access is faked — these tests must never reach the real DB.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.news_pipeline import PipelineResult
from services.pipeline import (
    ADMIN_CANCEL_ERROR,
    RECOVERY_STAGE,
    _decide_daily_recovery,
    _past_promote_time,
    _promote_if_late,
    recover_incomplete_daily_batch,
)

TODAY = "2026-10-21"


def _decide(
    run_status,
    *,
    stale=False,
    admin_cancelled=False,
    has_rank_checkpoint=False,
    has_post_rows=False,
    full_run_attempted=False,
):
    action, reason = _decide_daily_recovery(
        run_status,
        stale=stale,
        admin_cancelled=admin_cancelled,
        has_rank_checkpoint=has_rank_checkpoint,
        has_post_rows=has_post_rows,
        full_run_attempted=full_run_attempted,
    )
    assert reason, "every decision needs a reason for the promote log"
    return action


@pytest.mark.parametrize(
    "run_status, kwargs, expected",
    [
        # no run at all (cron never fired, Railway down at 07:12)
        (None, {}, "full_run"),
        (None, {"has_post_rows": True}, "skip"),
        # still inside the stale window: leave it alone
        ("running", {}, "skip"),
        ("running", {"has_rank_checkpoint": True}, "skip"),
        # died before rank (process killed / exception / 0 candidates)
        ("running", {"stale": True}, "full_run"),
        ("failed", {}, "full_run"),
        ("success", {}, "full_run"),
        # reached rank: existing write recovery
        ("failed", {"has_rank_checkpoint": True}, "write"),
        ("running", {"stale": True, "has_rank_checkpoint": True}, "write"),
        ("success", {"has_rank_checkpoint": True, "has_post_rows": True}, "write"),
        # guards
        ("failed", {"has_post_rows": True}, "skip"),
        ("failed", {"full_run_attempted": True}, "skip"),
        ("failed", {"admin_cancelled": True}, "skip"),
        ("failed", {"admin_cancelled": True, "has_rank_checkpoint": True}, "skip"),
    ],
)
def test_decide_daily_recovery_table(run_status, kwargs, expected):
    assert _decide(run_status, **kwargs) == expected


class _FakeTable:
    def __init__(self, db, name):
        self._db = db
        self._name = name
        self._op = "select"

    def select(self, *args, **kwargs):
        self._op = "select"
        return self

    def insert(self, row):
        self._op = "insert"
        self._db.inserts.append((self._name, row))
        return self

    def update(self, row):
        self._op = "update"
        self._db.updates.append((self._name, row))
        return self

    def eq(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        if self._op == "select":
            return MagicMock(data=self._db.rows.get(self._name, []))
        if self._op == "update":
            return MagicMock(data=[{"id": "claimed"}])
        return MagicMock(data=[])


class _FakeSupabase:
    def __init__(self, rows=None):
        self.rows = rows or {}
        self.inserts = []
        self.updates = []

    def table(self, name):
        return _FakeTable(self, name)


def _patches(supabase, *, rank_checkpoint=None, existing_rows=None):
    return (
        patch("services.pipeline.get_supabase", return_value=supabase),
        patch("services.pipeline.today_kst", return_value=TODAY),
        patch("services.pipeline._load_checkpoint", return_value=rank_checkpoint),
        patch("services.pipeline._fetch_daily_digest_rows_from_db", return_value=existing_rows or []),
        patch("services.pipeline.run_daily_pipeline", new_callable=AsyncMock),
        patch("services.pipeline.rerun_pipeline_stage", new_callable=AsyncMock),
        patch("services.pipeline.promote_drafts", new_callable=AsyncMock),
    )


@pytest.mark.asyncio
async def test_missing_run_gets_one_full_rerun_and_promotion():
    supabase = _FakeSupabase()
    p_sb, p_today, p_ckpt, p_rows, p_run, p_rerun, p_promote = _patches(supabase)
    with p_sb, p_today, p_ckpt, p_rows, p_run as run_mock, p_rerun as rerun_mock, p_promote as promote_mock:
        run_mock.return_value = PipelineResult(batch_id=TODAY, posts_created=4)
        promote_mock.return_value = {"promoted": 4, "kept_draft": 0, "errors": []}

        result = await recover_incomplete_daily_batch(TODAY, auto_publish=True)

    assert result["recovered"] == ["full_run"]
    run_mock.assert_awaited_once_with(
        batch_id=TODAY, skip_handbook=True, auto_publish=True, promote_when_late=False,
    )
    rerun_mock.assert_not_awaited()
    promote_mock.assert_awaited_once_with(batch_id=TODAY)

    run_inserts = [row for table, row in supabase.inserts if table == "pipeline_runs"]
    assert [row["run_key"] for row in run_inserts] == [f"news-{TODAY}"]
    log_inserts = [row for table, row in supabase.inserts if table == "pipeline_logs"]
    assert [row["pipeline_type"] for row in log_inserts] == [RECOVERY_STAGE]
    assert log_inserts[0]["debug_meta"]["action"] == "full_run"
    assert log_inserts[0]["run_id"] == run_inserts[0]["id"]


@pytest.mark.asyncio
async def test_cron_path_leaves_promotion_to_the_caller():
    supabase = _FakeSupabase({"pipeline_runs": [{"id": "run-1", "status": "failed"}]})
    p_sb, p_today, p_ckpt, p_rows, p_run, p_rerun, p_promote = _patches(supabase)
    with p_sb, p_today, p_ckpt, p_rows, p_run as run_mock, p_rerun, p_promote as promote_mock:
        run_mock.return_value = PipelineResult(batch_id=TODAY, posts_created=4)

        result = await recover_incomplete_daily_batch(
            TODAY, auto_publish=True, promote_after_recovery=False,
        )

    assert result["recovered"] == ["full_run"]
    promote_mock.assert_not_awaited()
    assert not [row for table, row in supabase.inserts if table == "pipeline_runs"]


@pytest.mark.asyncio
async def test_second_recovery_does_not_rerun_again():
    supabase = _FakeSupabase({
        "pipeline_runs": [{"id": "run-1", "status": "failed"}],
        "pipeline_logs": [{"debug_meta": {"action": "full_run", "reason": "earlier"}}],
    })
    p_sb, p_today, p_ckpt, p_rows, p_run, p_rerun, p_promote = _patches(supabase)
    with p_sb, p_today, p_ckpt, p_rows, p_run as run_mock, p_rerun, p_promote:
        result = await recover_incomplete_daily_batch(TODAY, auto_publish=True)

    run_mock.assert_not_awaited()
    assert result["recovered"] == []
    assert len(result["skipped"]) == 1


@pytest.mark.asyncio
async def test_admin_cancelled_run_is_not_recovered():
    supabase = _FakeSupabase({
        "pipeline_runs": [{"id": "run-1", "status": "failed", "last_error": ADMIN_CANCEL_ERROR}],
    })
    p_sb, p_today, p_ckpt, p_rows, p_run, p_rerun, p_promote = _patches(supabase)
    with p_sb, p_today, p_ckpt, p_rows, p_run as run_mock, p_rerun as rerun_mock, p_promote:
        result = await recover_incomplete_daily_batch(TODAY, auto_publish=True)

    run_mock.assert_not_awaited()
    rerun_mock.assert_not_awaited()
    assert result["recovered"] == []


@pytest.mark.asyncio
async def test_full_rerun_never_runs_for_a_past_batch():
    supabase = _FakeSupabase()
    p_sb, p_today, p_ckpt, p_rows, p_run, p_rerun, p_promote = _patches(supabase)
    with p_sb, p_today, p_ckpt, p_rows, p_run as run_mock, p_rerun, p_promote:
        result = await recover_incomplete_daily_batch("2026-10-19", auto_publish=True)

    run_mock.assert_not_awaited()
    assert "today" in result["skipped"][0]
    assert supabase.inserts == []


@pytest.mark.asyncio
async def test_full_rerun_crash_is_reported_not_raised():
    supabase = _FakeSupabase({"pipeline_runs": [{"id": "run-1", "status": "failed"}]})
    p_sb, p_today, p_ckpt, p_rows, p_run, p_rerun, p_promote = _patches(supabase)
    with p_sb, p_today, p_ckpt, p_rows, p_run as run_mock, p_rerun, p_promote as promote_mock:
        run_mock.side_effect = RuntimeError("boom")

        result = await recover_incomplete_daily_batch(TODAY, auto_publish=True)

    assert result["recovered"] == []
    assert result["errors"] == ["full rerun crashed: boom"]
    promote_mock.assert_not_awaited()


# --- RECOVERY-STALE-01: stale = no activity, not time since start ----------

def _ago(minutes: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


@pytest.mark.asyncio
async def test_slow_run_still_logging_at_0900_is_left_alone():
    # Started 108 minutes ago (07:12 -> 09:00) but logged 10 minutes ago: alive.
    supabase = _FakeSupabase({
        "pipeline_runs": [{"id": "run-1", "status": "running", "started_at": _ago(108)}],
        "pipeline_logs": [{"created_at": _ago(10)}],
    })
    p_sb, p_today, p_ckpt, p_rows, p_run, p_rerun, p_promote = _patches(supabase, rank_checkpoint={"research": [{}]})
    with p_sb, p_today, p_ckpt, p_rows, p_run as run_mock, p_rerun as rerun_mock, p_promote:
        result = await recover_incomplete_daily_batch(TODAY, auto_publish=True)

    assert result["skipped"] == ["run is still running"]
    run_mock.assert_not_awaited()
    rerun_mock.assert_not_awaited()
    assert supabase.updates == []


@pytest.mark.asyncio
async def test_run_silent_past_the_window_is_claimed_and_recovered():
    supabase = _FakeSupabase({
        "pipeline_runs": [{"id": "run-1", "status": "running", "started_at": _ago(108)}],
        "pipeline_logs": [{"created_at": _ago(100)}],
    })
    p_sb, p_today, p_ckpt, p_rows, p_run, p_rerun, p_promote = _patches(supabase)
    with p_sb, p_today, p_ckpt, p_rows, p_run as run_mock, p_rerun, p_promote:
        run_mock.return_value = PipelineResult(batch_id=TODAY, posts_created=4)
        result = await recover_incomplete_daily_batch(
            TODAY, auto_publish=True, promote_after_recovery=False,
        )

    assert result["recovered"] == ["full_run"]
    claimed = [row for table, row in supabase.updates if table == "pipeline_runs"]
    assert claimed and "no activity" in claimed[0]["last_error"]


def test_promote_time_is_0900_kst_on_the_batch_date():
    assert not _past_promote_time("2026-10-21", datetime(2026, 10, 20, 23, 59, tzinfo=timezone.utc))
    assert _past_promote_time("2026-10-21", datetime(2026, 10, 21, 0, 0, tzinfo=timezone.utc))
    assert not _past_promote_time("not-a-date")


@pytest.mark.asyncio
async def test_late_run_promotes_its_own_drafts_only_after_0900():
    with patch("services.pipeline.promote_drafts", new_callable=AsyncMock) as promote_mock:
        promote_mock.return_value = {"promoted": 4}
        early = await _promote_if_late("2026-10-21", datetime(2026, 10, 20, 22, 30, tzinfo=timezone.utc))
        late = await _promote_if_late("2026-10-21", datetime(2026, 10, 21, 0, 40, tzinfo=timezone.utc))

    assert early is None
    assert late == {"promoted": 4}
    promote_mock.assert_awaited_once_with(batch_id="2026-10-21")


@pytest.mark.asyncio
async def test_late_self_promotion_failure_is_swallowed():
    with patch("services.pipeline.promote_drafts", new_callable=AsyncMock, side_effect=RuntimeError("db down")):
        assert await _promote_if_late("2026-10-21", datetime(2026, 10, 21, 1, 0, tzinfo=timezone.utc)) is None

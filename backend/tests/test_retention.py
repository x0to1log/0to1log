"""Retention policy for pipeline debug data (checkpoints, log debug_meta)."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

from postgrest.types import CountMethod, ReturnMethod

from services.retention import (
    CHECKPOINT_RETENTION_DAYS,
    DEBUG_META_RETENTION_DAYS,
    prune_pipeline_debug_data,
)


def _fake_supabase():
    sb = MagicMock()
    sb.table.return_value = sb
    sb.delete.return_value = sb
    sb.update.return_value = sb
    sb.lt.return_value = sb
    sb.not_ = sb
    sb.is_.return_value = sb
    sb.execute.return_value = MagicMock(data=[], count=2)
    return sb


def test_retention_windows_match_decision():
    assert CHECKPOINT_RETENTION_DAYS == 14
    assert DEBUG_META_RETENTION_DAYS == 60


def test_prune_deletes_old_checkpoints_and_clears_old_debug_meta():
    sb = _fake_supabase()
    now = datetime(2026, 10, 14, tzinfo=timezone.utc)

    result = prune_pipeline_debug_data(sb, now=now)

    tables = [c.args[0] for c in sb.table.call_args_list]
    assert tables == ["pipeline_checkpoints", "pipeline_logs"]
    sb.delete.assert_called_once_with(count=CountMethod.exact, returning=ReturnMethod.minimal)
    sb.update.assert_called_once_with(
        {"debug_meta": None}, count=CountMethod.exact, returning=ReturnMethod.minimal,
    )
    cutoffs = [c.args for c in sb.lt.call_args_list]
    assert cutoffs == [
        ("created_at", "2026-09-30T00:00:00+00:00"),
        ("created_at", "2026-08-15T00:00:00+00:00"),
    ]
    sb.is_.assert_called_once_with("debug_meta", "null")
    assert result == {"checkpoints_deleted": 2, "debug_meta_cleared": 2, "errors": []}


def test_prune_reports_errors_without_raising():
    sb = _fake_supabase()
    sb.execute.side_effect = [RuntimeError("boom"), MagicMock(data=[], count=0)]

    result = prune_pipeline_debug_data(sb, now=datetime(2026, 10, 14, tzinfo=timezone.utc))

    assert result["checkpoints_deleted"] == 0
    assert result["debug_meta_cleared"] == 0
    assert len(result["errors"]) == 1 and "pipeline_checkpoints" in result["errors"][0]

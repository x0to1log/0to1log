import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

from services.pipeline import (
    acquire_pipeline_lock,
    release_pipeline_lock,
    STALE_THRESHOLD_SECONDS,
)


def _make_supabase_mock():
    """Create a mock Supabase client with chained query methods."""
    mock = MagicMock()

    # Make table().select().eq().maybe_single().execute() work
    chain = mock.table.return_value
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.maybe_single.return_value = chain
    chain.insert.return_value = chain
    chain.update.return_value = chain

    return mock


def _iso(dt: datetime) -> str:
    return dt.isoformat()


@pytest.mark.asyncio
async def test_acquire_new_lock():
    """No existing record → INSERT new row → return run_id."""
    mock_client = _make_supabase_mock()

    # select returns no existing record
    mock_client.table.return_value.execute.side_effect = [
        MagicMock(data=None),  # maybe_single → no row
        MagicMock(data=[{"id": "new-run-id"}]),  # insert
    ]

    with patch("services.pipeline.get_supabase", return_value=mock_client):
        result = await acquire_pipeline_lock("2026-03-06")

    assert result == "new-run-id"
    mock_client.table.return_value.insert.assert_called_once()


@pytest.mark.asyncio
async def test_skip_running_lock():
    """Running lock within 1 hour → return None (skip)."""
    mock_client = _make_supabase_mock()

    recent_start = _iso(datetime.now(timezone.utc) - timedelta(minutes=30))
    mock_client.table.return_value.execute.return_value = MagicMock(
        data={"id": "existing-id", "status": "running", "started_at": recent_start}
    )

    with patch("services.pipeline.get_supabase", return_value=mock_client):
        result = await acquire_pipeline_lock("2026-03-06")

    assert result is None
    mock_client.table.return_value.update.assert_not_called()


@pytest.mark.asyncio
async def test_recover_stale_lock():
    """Running lock older than 1 hour → UPDATE existing row → return run_id."""
    mock_client = _make_supabase_mock()

    stale_start = _iso(datetime.now(timezone.utc) - timedelta(hours=2))

    # First call: select returns stale running row
    # Second call: update succeeds
    mock_client.table.return_value.execute.side_effect = [
        MagicMock(data={"id": "stale-id", "status": "running", "started_at": stale_start}),
        MagicMock(data=None),  # update result
    ]

    with patch("services.pipeline.get_supabase", return_value=mock_client):
        result = await acquire_pipeline_lock("2026-03-06")

    assert result == "stale-id"
    mock_client.table.return_value.update.assert_called_once()
    # Verify no INSERT was called (reuse existing row)
    mock_client.table.return_value.insert.assert_not_called()


@pytest.mark.asyncio
async def test_skip_success():
    """Already succeeded → return None."""
    mock_client = _make_supabase_mock()

    mock_client.table.return_value.execute.return_value = MagicMock(
        data={"id": "done-id", "status": "success", "started_at": _iso(datetime.now(timezone.utc))}
    )

    with patch("services.pipeline.get_supabase", return_value=mock_client):
        result = await acquire_pipeline_lock("2026-03-06")

    assert result is None


@pytest.mark.asyncio
async def test_retry_after_failed():
    """Failed status → UPDATE existing row → return run_id."""
    mock_client = _make_supabase_mock()

    mock_client.table.return_value.execute.side_effect = [
        MagicMock(data={"id": "failed-id", "status": "failed", "started_at": _iso(datetime.now(timezone.utc))}),
        MagicMock(data=None),  # update result
    ]

    with patch("services.pipeline.get_supabase", return_value=mock_client):
        result = await acquire_pipeline_lock("2026-03-06")

    assert result == "failed-id"
    mock_client.table.return_value.update.assert_called_once()
    mock_client.table.return_value.insert.assert_not_called()


@pytest.mark.asyncio
async def test_release_lock_success():
    """Release lock with success status."""
    mock_client = _make_supabase_mock()
    mock_client.table.return_value.execute.return_value = MagicMock()

    with patch("services.pipeline.get_supabase", return_value=mock_client):
        await release_pipeline_lock("run-123", "success")

    mock_client.table.return_value.update.assert_called_once()
    call_args = mock_client.table.return_value.update.call_args[0][0]
    assert call_args["status"] == "success"
    assert "finished_at" in call_args


@pytest.mark.asyncio
async def test_release_lock_failed_with_error():
    """Release lock with failed status and error message."""
    mock_client = _make_supabase_mock()
    mock_client.table.return_value.execute.return_value = MagicMock()

    with patch("services.pipeline.get_supabase", return_value=mock_client):
        await release_pipeline_lock("run-456", "failed", "Something broke")

    call_args = mock_client.table.return_value.update.call_args[0][0]
    assert call_args["status"] == "failed"
    assert call_args["last_error"] == "Something broke"


@pytest.mark.asyncio
async def test_no_supabase_returns_none():
    """If Supabase is not configured, return None gracefully."""
    with patch("services.pipeline.get_supabase", return_value=None):
        result = await acquire_pipeline_lock("2026-03-06")
    assert result is None

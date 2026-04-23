"""Tests for weekly per-persona regeneration (admin endpoint + helper)."""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from core.security import require_admin


def _admin_ok():
    """Dependency override returning a fake admin user (bypasses Bearer+DB check)."""
    return {"email": "admin@test", "is_active": True}


def test_regenerate_endpoint_requires_auth_without_token_401():
    """POST without Authorization header → 401."""
    from main import app
    client = TestClient(app)
    resp = client.post(
        "/api/admin/weekly/regenerate",
        json={"week_id": "2026-W16", "persona": "expert"},
    )
    # require_admin raises 401 when no Bearer token present
    assert resp.status_code in (401, 403), resp.text


def test_regenerate_endpoint_invalid_persona_returns_400():
    """Invalid persona → 400 (ValueError in regenerate_weekly_persona)."""
    from main import app
    app.dependency_overrides[require_admin] = _admin_ok
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/admin/weekly/regenerate",
            json={"week_id": "2026-W16", "persona": "bogus"},
        )
        assert resp.status_code == 400
        assert "expert" in resp.text or "learner" in resp.text
    finally:
        app.dependency_overrides.clear()


def test_regenerate_endpoint_happy_path_calls_helper():
    """Valid request with admin override → helper called, 200 return."""
    from main import app
    app.dependency_overrides[require_admin] = _admin_ok

    fake_result = {
        "status": "success",
        "run_id": "test-run",
        "week_id": "2026-W16",
        "persona": "expert",
        "quality_score": 85,
        "en_chars": 12345,
        "ko_chars": 9876,
        "cost_usd": 0.15,
    }

    try:
        with patch(
            "routers.admin_weekly.regenerate_weekly_persona",
            new=AsyncMock(return_value=fake_result),
        ) as mock_fn:
            client = TestClient(app)
            resp = client.post(
                "/api/admin/weekly/regenerate",
                json={"week_id": "2026-W16", "persona": "expert"},
            )
            assert resp.status_code == 200
            assert resp.json() == fake_result
            mock_fn.assert_awaited_once_with("2026-W16", "expert", run_id=None)
    finally:
        app.dependency_overrides.clear()


def test_regenerate_endpoint_forwards_run_id_when_present():
    """When the dropdown passes run_id, it flows through to the helper so
    new stages append to the original run instead of creating a new one."""
    from main import app
    app.dependency_overrides[require_admin] = _admin_ok
    fake_result = {"status": "success", "run_id": "orig-run-id", "quality_score": 88}
    try:
        with patch(
            "routers.admin_weekly.regenerate_weekly_persona",
            new=AsyncMock(return_value=fake_result),
        ) as mock_fn:
            client = TestClient(app)
            resp = client.post(
                "/api/admin/weekly/regenerate",
                json={"week_id": "2026-W16", "persona": "learner", "run_id": "orig-run-id"},
            )
            assert resp.status_code == 200
            mock_fn.assert_awaited_once_with("2026-W16", "learner", run_id="orig-run-id")
    finally:
        app.dependency_overrides.clear()


def test_regenerate_endpoint_runtime_error_returns_409():
    """Helper RuntimeError (e.g. no existing rows) → 409 Conflict."""
    from main import app
    app.dependency_overrides[require_admin] = _admin_ok
    try:
        with patch(
            "routers.admin_weekly.regenerate_weekly_persona",
            new=AsyncMock(side_effect=RuntimeError("Existing weekly rows not found")),
        ):
            client = TestClient(app)
            resp = client.post(
                "/api/admin/weekly/regenerate",
                json={"week_id": "2026-W99", "persona": "learner"},
            )
            assert resp.status_code == 409
            assert "Existing weekly rows" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_regenerate_helper_rejects_invalid_persona():
    """regenerate_weekly_persona raises ValueError for invalid persona."""
    import services.pipeline  # noqa: F401 — resolve circular import before touching helpers
    from services.pipeline import regenerate_weekly_persona
    with pytest.raises(ValueError, match="expert.*learner"):
        await regenerate_weekly_persona("2026-W16", "bogus")

"""Integration tests — CORS, health, admin auth, cron auth."""

from unittest.mock import patch

import httpx
import pytest

from main import app

ALLOWED_ORIGIN = "http://localhost:4321"
VALID_CRON_SECRET = "integration-test-secret"


@pytest.fixture()
def async_client():
    """Create an httpx AsyncClient bound to the ASGI app."""
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


# ── 1. CORS preflight ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cors_preflight_returns_allowed_origin(async_client):
    """OPTIONS /health from allowed origin includes access-control-allow-origin."""
    response = await async_client.options(
        "/health",
        headers={
            "origin": ALLOWED_ORIGIN,
            "access-control-request-method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


# ── 2. Health endpoint ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health_returns_200_with_status_and_timestamp(async_client):
    """GET /health returns 200 with status ok and a timestamp."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


# ── 3. Admin 401 ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_drafts_without_auth_returns_401(async_client):
    """GET /api/admin/drafts without Authorization header returns 401."""
    response = await async_client.get("/api/admin/drafts")
    assert response.status_code == 401


# ── 4. Cron without secret ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_cron_without_secret_returns_401(async_client, monkeypatch):
    """POST /api/cron/news-pipeline without x-cron-secret returns 401."""
    monkeypatch.setattr("core.config.settings.cron_secret", VALID_CRON_SECRET)
    response = await async_client.post("/api/cron/news-pipeline")
    assert response.status_code == 401


# ── 5. Cron with valid secret ───────────────────────────────────────


@pytest.mark.asyncio
async def test_cron_with_valid_secret_returns_202(async_client, monkeypatch):
    """POST /api/cron/news-pipeline with correct secret returns 202."""
    monkeypatch.setattr("core.config.settings.cron_secret", VALID_CRON_SECRET)
    with patch("routers.cron.run_daily_pipeline"):
        response = await async_client.post(
            "/api/cron/news-pipeline",
            headers={"x-cron-secret": VALID_CRON_SECRET},
        )
    assert response.status_code == 202
    data = response.json()
    assert data["accepted"] is True
    assert "message" in data

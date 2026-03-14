"""Integration tests — CORS and health endpoint."""

import httpx
import pytest

from main import app


ALLOWED_ORIGIN = "http://localhost:4321"


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

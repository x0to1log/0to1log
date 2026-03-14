"""Tests for cron endpoint."""
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


def test_cron_news_pipeline_returns_202():
    """POST /api/cron/news-pipeline with valid secret returns 202."""
    with patch("routers.cron.run_daily_pipeline", new_callable=AsyncMock) as mock_pipeline:
        from main import app
        client = TestClient(app)

        with patch("core.security.settings") as mock_settings:
            mock_settings.cron_secret = "test-secret-123"

            response = client.post(
                "/api/cron/news-pipeline",
                headers={"x-cron-secret": "test-secret-123"},
            )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert "batch_id" in data
        mock_pipeline.assert_called_once()


def test_cron_news_pipeline_missing_secret_returns_401():
    """POST without x-cron-secret header returns 401."""
    from main import app
    client = TestClient(app)

    with patch("core.security.settings") as mock_settings:
        mock_settings.cron_secret = "test-secret-123"

        response = client.post("/api/cron/news-pipeline")

    assert response.status_code == 401


def test_cron_news_pipeline_wrong_secret_returns_401():
    """POST with wrong secret returns 401."""
    from main import app
    client = TestClient(app)

    with patch("core.security.settings") as mock_settings:
        mock_settings.cron_secret = "test-secret-123"

        response = client.post(
            "/api/cron/news-pipeline",
            headers={"x-cron-secret": "wrong-secret"},
        )

    assert response.status_code == 401


def test_cron_health_returns_200():
    """GET /api/cron/health returns 200 with pipeline info."""
    from main import app
    client = TestClient(app)

    response = client.get("/api/cron/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "pipeline" in data

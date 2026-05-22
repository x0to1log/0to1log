"""Tests for cron endpoint."""
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


def test_cron_news_pipeline_returns_202():
    """POST /api/cron/news-pipeline with valid secret returns 202."""
    with patch("routers.cron.run_daily_pipeline", new_callable=AsyncMock) as mock_pipeline, \
         patch("routers.cron.check_existing_batch", return_value=None):
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


def test_promote_drafts_attempts_incomplete_batch_recovery_first():
    """The publish cron should repair missing research/business rows before promotion."""
    with patch("routers.cron.recover_incomplete_daily_batch", new_callable=AsyncMock) as recover_mock, \
         patch("routers.cron.promote_drafts", new_callable=AsyncMock) as promote_mock:
        recover_mock.return_value = {"recovered": ["research"], "errors": []}
        promote_mock.return_value = {"promoted": 2, "kept_draft": 0, "errors": []}

        from main import app
        client = TestClient(app)

        with patch("core.security.settings") as mock_settings:
            mock_settings.cron_secret = "test-secret-123"

            response = client.post(
                "/api/cron/promote-drafts",
                headers={"x-cron-secret": "test-secret-123"},
                json={"batch_id": "2026-05-22"},
            )

    assert response.status_code == 202
    recover_mock.assert_awaited_once_with(
        batch_id="2026-05-22",
        auto_publish=True,
        promote_after_recovery=False,
    )
    promote_mock.assert_awaited_once_with(batch_id="2026-05-22")

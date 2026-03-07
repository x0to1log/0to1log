"""Tests for Cron endpoint — secret validation + 202 response."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

VALID_SECRET = "test-cron-secret"


@pytest.fixture(autouse=True)
def set_cron_secret(monkeypatch):
    """Set a known cron secret for testing."""
    monkeypatch.setattr("core.config.settings.cron_secret", VALID_SECRET)


class TestCronAuth:
    def test_missing_secret_returns_401(self):
        """No x-cron-secret header -> 401."""
        response = client.post("/api/cron/news-pipeline")
        assert response.status_code == 401

    def test_invalid_secret_returns_401(self):
        """Wrong x-cron-secret header -> 401."""
        response = client.post(
            "/api/cron/news-pipeline",
            headers={"x-cron-secret": "wrong-secret"},
        )
        assert response.status_code == 401

    def test_empty_secret_returns_401(self):
        """Empty x-cron-secret header -> 401."""
        response = client.post(
            "/api/cron/news-pipeline",
            headers={"x-cron-secret": ""},
        )
        assert response.status_code == 401


class TestCronPipeline:
    @patch("routers.cron.run_daily_pipeline")
    def test_valid_secret_returns_202(self, mock_pipeline):
        """Valid secret -> 202 Accepted."""
        response = client.post(
            "/api/cron/news-pipeline",
            headers={"x-cron-secret": VALID_SECRET},
        )
        assert response.status_code == 202
        mock_pipeline.assert_called_once()

    @patch("routers.cron.run_daily_pipeline")
    def test_response_body_format(self, mock_pipeline):
        """202 response has accepted=true and message."""
        response = client.post(
            "/api/cron/news-pipeline",
            headers={"x-cron-secret": VALID_SECRET},
        )
        data = response.json()
        assert data["accepted"] is True
        assert "message" in data

    @patch("routers.cron.run_daily_pipeline")
    def test_response_model_matches_schema(self, mock_pipeline):
        """Response matches PipelineAcceptedResponse schema."""
        response = client.post(
            "/api/cron/news-pipeline",
            headers={"x-cron-secret": VALID_SECRET},
        )
        data = response.json()
        assert set(data.keys()) == {"accepted", "message"}

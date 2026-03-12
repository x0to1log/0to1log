"""Tests for Admin CRUD endpoints with auth 401/403 split."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from core.security import require_admin

client = TestClient(app)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_DRAFT = {
    "id": "uuid-001",
    "title": "Test Draft Post",
    "slug": "2026-03-07-business-daily",
    "category": "ai-news",
    "post_type": "business",
    "status": "draft",
    "locale": "en",
    "content_beginner": "Simple explanation...",
    "content_learner": "More detailed...",
    "content_expert": "Expert analysis...",
    "guide_items": {
        "one_liner": "Test one liner",
        "action_item": "Test action",
        "critical_gotcha": "Test gotcha",
        "rotating_item": "Test rotating",
        "quiz_poll": {
            "question": "Test?",
            "options": ["A", "B"],
            "answer": "A",
            "explanation": "Because A",
        },
    },
    "related_news": {"big_tech": None, "industry_biz": None, "new_tools": None},
    "source_urls": ["https://example.com"],
    "news_temperature": 3,
    "tags": ["test"],
    "pipeline_batch_id": "2026-03-07",
    "created_at": "2026-03-07T06:00:00Z",
    "updated_at": "2026-03-07T06:00:00Z",
}


def _fake_admin():
    """Override for require_admin dependency."""
    user = MagicMock()
    user.email = "admin@0to1log.com"
    return user


def _mock_supabase_with_data(data):
    """Create a mock Supabase client that returns the given data."""
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.data = data

    # Chain: client.table().select().eq().order().execute()
    mock_table = mock_client.table.return_value
    mock_select = mock_table.select.return_value
    mock_eq = mock_select.eq.return_value
    mock_eq.order.return_value.execute.return_value = mock_result
    mock_eq.eq.return_value.maybe_single.return_value.execute.return_value = mock_result

    # For update chain: client.table().update().eq().eq().execute()
    mock_update = mock_table.update.return_value
    mock_update.eq.return_value.eq.return_value.execute.return_value = mock_result

    return mock_client


@pytest.fixture
def admin_client():
    """TestClient with require_admin dependency overridden."""
    app.dependency_overrides[require_admin] = _fake_admin
    yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth Tests — 401/403 split
# ---------------------------------------------------------------------------

class TestAuthSplit:
    def test_no_token_returns_401(self):
        """Missing Authorization header -> 401."""
        response = client.get("/api/admin/drafts")
        assert response.status_code == 401

    def test_invalid_token_returns_401(self):
        """Invalid Bearer token -> 401."""
        response = client.get(
            "/api/admin/drafts",
            headers={"Authorization": "Bearer invalid-token"},
        )
        # Without supabase configured, expect 401 or 503
        assert response.status_code in (401, 503)

    def test_non_admin_returns_403(self):
        """Valid token but not in admin_users -> 403."""
        mock_sb = MagicMock()
        mock_user = MagicMock()
        mock_user.user.email = "notadmin@example.com"
        mock_sb.auth.get_user.return_value = mock_user

        admin_result = MagicMock()
        admin_result.data = None
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = admin_result

        with patch("core.security.get_supabase", return_value=mock_sb):
            response = client.get(
                "/api/admin/drafts",
                headers={"Authorization": "Bearer valid-but-not-admin"},
            )
        assert response.status_code == 403

    def test_all_admin_endpoints_require_auth(self):
        """All admin endpoints return 401 without token."""
        endpoints = [
            ("GET", "/api/admin/drafts"),
            ("GET", "/api/admin/drafts/test-slug"),
            ("PATCH", "/api/admin/posts/uuid-001/publish"),
            ("PATCH", "/api/admin/posts/uuid-001/update"),
        ]
        for method, path in endpoints:
            response = client.request(method, path)
            assert response.status_code == 401, f"{method} {path} should require auth"


# ---------------------------------------------------------------------------
# CRUD Tests (with mocked auth + db)
# ---------------------------------------------------------------------------

class TestListDrafts:
    def test_list_drafts_returns_200(self, admin_client):
        mock_db = _mock_supabase_with_data([SAMPLE_DRAFT])

        with patch("routers.admin.get_supabase", return_value=mock_db):
            response = admin_client.get("/api/admin/drafts")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["slug"] == "2026-03-07-business-daily"

    def test_list_drafts_empty(self, admin_client):
        mock_db = _mock_supabase_with_data([])

        with patch("routers.admin.get_supabase", return_value=mock_db):
            response = admin_client.get("/api/admin/drafts")

        assert response.status_code == 200
        assert response.json() == []


class TestGetDraft:
    def test_get_draft_returns_200(self, admin_client):
        mock_db = _mock_supabase_with_data(SAMPLE_DRAFT)

        with patch("routers.admin.get_supabase", return_value=mock_db):
            response = admin_client.get("/api/admin/drafts/2026-03-07-business-daily")

        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "2026-03-07-business-daily"
        assert data["content_beginner"] is not None

    def test_get_draft_not_found_returns_404(self, admin_client):
        mock_db = _mock_supabase_with_data(None)

        with patch("routers.admin.get_supabase", return_value=mock_db):
            response = admin_client.get("/api/admin/drafts/nonexistent")

        assert response.status_code == 404


class TestPublishPost:
    def test_publish_returns_200(self, admin_client):
        published_row = {
            **SAMPLE_DRAFT,
            "status": "published",
            "published_at": "2026-03-07T12:00:00Z",
        }
        mock_db = _mock_supabase_with_data([published_row])
        mock_embed = AsyncMock()

        with patch("routers.admin.get_supabase", return_value=mock_db), \
             patch("routers.admin.embed_post", mock_embed):
            response = admin_client.patch("/api/admin/posts/uuid-001/publish")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "published"
        assert data["published_at"] is not None
        mock_embed.assert_awaited_once()

    def test_publish_not_found_returns_404(self, admin_client):
        mock_db = _mock_supabase_with_data([])

        with patch("routers.admin.get_supabase", return_value=mock_db):
            response = admin_client.patch("/api/admin/posts/nonexistent/publish")

        assert response.status_code == 404


class TestUpdatePost:
    def test_update_returns_200(self, admin_client):
        updated_row = {**SAMPLE_DRAFT, "title": "Updated Title"}
        mock_db = _mock_supabase_with_data([updated_row])

        with patch("routers.admin.get_supabase", return_value=mock_db):
            response = admin_client.patch(
                "/api/admin/posts/uuid-001/update",
                json={"title": "Updated Title"},
            )

        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    def test_update_empty_body_returns_422(self, admin_client):
        mock_db = _mock_supabase_with_data([])

        with patch("routers.admin.get_supabase", return_value=mock_db):
            response = admin_client.patch(
                "/api/admin/posts/uuid-001/update",
                json={},
            )

        assert response.status_code == 422

    def test_update_not_found_returns_404(self, admin_client):
        mock_db = _mock_supabase_with_data([])

        with patch("routers.admin.get_supabase", return_value=mock_db):
            response = admin_client.patch(
                "/api/admin/posts/nonexistent/update",
                json={"title": "New Title"},
            )

        assert response.status_code == 404

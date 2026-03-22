"""Tests for handbook post-processing: ref URL validation."""

import asyncio
from unittest.mock import AsyncMock, patch

from services.agents.advisor import _validate_ref_urls


# --- _validate_ref_urls ---


class TestValidateRefUrls:
    def test_removes_broken_links(self):
        content = (
            "- [PyTorch Docs](https://fake-broken-url.invalid/docs) — 공식 문서\n"
            "- Some plain text"
        )

        mock_resp = AsyncMock()
        mock_resp.status_code = 404

        mock_client = AsyncMock()
        mock_client.head.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("services.agents.advisor.httpx.AsyncClient", return_value=mock_client):
            result = asyncio.get_event_loop().run_until_complete(
                _validate_ref_urls(content)
            )
        assert "PyTorch Docs" in result
        assert "https://fake-broken-url.invalid" not in result

    def test_keeps_valid_links(self):
        content = "- [Google](https://www.google.com) — 검색 엔진"

        mock_resp = AsyncMock()
        mock_resp.status_code = 200

        mock_client = AsyncMock()
        mock_client.head.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("services.agents.advisor.httpx.AsyncClient", return_value=mock_client):
            result = asyncio.get_event_loop().run_until_complete(
                _validate_ref_urls(content)
            )
        assert "[Google](https://www.google.com)" in result

    def test_no_links_returns_unchanged(self):
        content = "Just plain text without any links."
        result = asyncio.get_event_loop().run_until_complete(
            _validate_ref_urls(content)
        )
        assert result == content

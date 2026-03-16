"""Tests for handbook post-processing: related term linking + ref URL validation."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from services.agents.advisor import _link_related_terms, _validate_ref_urls


# --- _link_related_terms ---


class TestLinkRelatedTerms:
    def setup_method(self):
        self.handbook_map = {
            "ARIMA": "arima",
            "Transformer": "transformer",
            "LSTM": "lstm",
            "CNN": "cnn",
        }

    def test_links_bold_term_that_exists(self):
        content = "- **ARIMA** — AR 모델의 확장"
        result = _link_related_terms(content, self.handbook_map)
        assert result == "- [**ARIMA**](/handbook/arima/) — AR 모델의 확장"

    def test_does_not_link_unknown_term(self):
        content = "- **RandomForest** — 앙상블 방법"
        result = _link_related_terms(content, self.handbook_map)
        assert result == "- **RandomForest** — 앙상블 방법"

    def test_case_insensitive_match(self):
        content = "- **transformer** — 어텐션 기반 아키텍처"
        result = _link_related_terms(content, self.handbook_map)
        assert result == "- [**transformer**](/handbook/transformer/) — 어텐션 기반 아키텍처"

    def test_multiple_terms(self):
        content = (
            "- **LSTM** — 장단기 기억 네트워크\n"
            "- **CNN** — 합성곱 신경망\n"
            "- **GAN** — 생성적 적대 신경망"
        )
        result = _link_related_terms(content, self.handbook_map)
        assert "[**LSTM**](/handbook/lstm/)" in result
        assert "[**CNN**](/handbook/cnn/)" in result
        assert "**GAN**" in result  # not linked (not in map)
        assert "[**GAN**]" not in result

    def test_skips_already_linked_term(self):
        content = "- [**ARIMA**](/handbook/arima/) — already linked"
        result = _link_related_terms(content, self.handbook_map)
        # Should not double-link
        assert result.count("/handbook/arima/") == 1

    def test_empty_map(self):
        content = "- **ARIMA** — some description"
        result = _link_related_terms(content, {})
        assert result == content

    def test_no_bold_terms(self):
        content = "No bold terms here, just plain text."
        result = _link_related_terms(content, self.handbook_map)
        assert result == content


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

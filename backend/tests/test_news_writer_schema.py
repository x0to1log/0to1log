"""Tests for the news writer strict JSON schema + Pydantic models."""
import pytest
from pydantic import ValidationError

from services.agents.schemas.news_writer import (
    NewsWriterOutput,
    Citation,
    build_news_writer_json_schema,
)


def _valid_output_payload() -> dict:
    return {
        "headline": "Foo launches bar",
        "headline_ko": "푸가 바 출시",
        "excerpt": "summary",
        "excerpt_ko": "요약",
        "en": "Foo launched [CITE_1] today.",
        "ko": "푸는 오늘 [CITE_1] 출시했다.",
        "citations": [{"n": 1, "url": "https://example.com/a"}],
        "tags": ["ai"],
        "focus_items": ["foo"],
        "focus_items_ko": ["푸"],
        "quiz": {
            "en": {"q": "Q?", "a": "A", "options": ["A", "B", "C", "D"]},
            "ko": {"q": "Q?", "a": "A", "options": ["A", "B", "C", "D"]},
        },
    }


def test_valid_output_passes():
    out = NewsWriterOutput(**_valid_output_payload())
    assert out.citations[0].url == "https://example.com/a"


def test_empty_citations_allowed_for_zero_citation_body():
    payload = _valid_output_payload()
    payload["en"] = "No citations here."
    payload["ko"] = "인용 없음."
    payload["citations"] = []
    NewsWriterOutput(**payload)


def test_citation_without_url_rejected():
    with pytest.raises(ValidationError):
        Citation(n=1, url="")


def test_citation_url_must_be_http():
    with pytest.raises(ValidationError):
        Citation(n=1, url="ftp://example.com/file")


def test_build_schema_embeds_enum_from_allowlist():
    allowlist = ["https://a.com", "https://b.com/p"]
    schema = build_news_writer_json_schema(allowlist)
    citation_item = schema["schema"]["properties"]["citations"]["items"]
    assert citation_item["properties"]["url"]["enum"] == allowlist
    assert schema["strict"] is True
    assert citation_item["additionalProperties"] is False


def test_build_schema_dedupes_allowlist_preserving_order():
    allowlist = ["https://a.com", "https://b.com", "https://a.com"]
    schema = build_news_writer_json_schema(allowlist)
    enum_urls = schema["schema"]["properties"]["citations"]["items"]["properties"]["url"]["enum"]
    assert enum_urls == ["https://a.com", "https://b.com"]


def test_build_schema_with_empty_allowlist_raises():
    with pytest.raises(ValueError):
        build_news_writer_json_schema([])

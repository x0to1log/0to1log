"""Tests for the news writer strict JSON schema + Pydantic models."""

import pytest
from pydantic import ValidationError

from services.agents.schemas.news_writer import (
    Citation,
    NewsWriterOutput,
    build_news_writer_json_schema,
)


def _valid_output_payload() -> dict:
    return {
        "headline": "Foo launches bar",
        "headline_ko": "Foo launches bar",
        "excerpt": "summary",
        "excerpt_ko": "summary",
        "en": "Foo launched [CITE_1] today.",
        "ko": "Foo launched [CITE_1] today.",
        "citations": [{"n": 1, "url": "https://example.com/a"}],
        "tags": ["ai"],
        "focus_items": ["foo"],
        "focus_items_ko": ["foo"],
        "sources": [
            {"id": 1, "url": "https://example.com/a", "title": "Primary source"}
        ],
    }


def test_valid_output_passes():
    out = NewsWriterOutput(**_valid_output_payload())
    assert out.citations[0].url == "https://example.com/a"


def test_empty_citations_allowed_for_zero_citation_body():
    payload = _valid_output_payload()
    payload["en"] = "No citations here."
    payload["ko"] = "No citations here."
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


def test_writer_schema_does_not_generate_quizzes():
    schema = build_news_writer_json_schema(["https://a.com"])
    props = schema["schema"]["properties"]

    assert "quiz_en" not in props
    assert "quiz_ko" not in props
    assert "quiz" not in props
    assert "quiz_en" not in schema["schema"]["required"]
    assert "quiz_ko" not in schema["schema"]["required"]


def test_schema_includes_sources_required():
    """Writer must emit sources[] for title/publisher metadata."""

    schema = build_news_writer_json_schema(["https://a.com"])
    props = schema["schema"]["properties"]
    assert "sources" in props
    assert "sources" in schema["schema"]["required"]
    source_item = props["sources"]["items"]
    assert set(source_item["required"]) == {"id", "url", "title"}
    assert source_item["additionalProperties"] is False


def test_sources_empty_list_allowed():
    """Edge case: digest with zero citations should still satisfy schema."""

    payload = _valid_output_payload()
    payload["sources"] = []
    payload["citations"] = []
    payload["en"] = "No citations needed."
    payload["ko"] = "No citations needed."
    NewsWriterOutput(**payload)

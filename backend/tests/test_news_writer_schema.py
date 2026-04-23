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
        "quiz_en": {
            "question": "What happened?",
            "answer": "A",
            "options": ["A", "B", "C", "D"],
            "explanation": "Because A.",
        },
        "quiz_ko": {
            "question": "무엇이 일어났나?",
            "answer": "가",
            "options": ["가", "나", "다", "라"],
            "explanation": "가 맞습니다.",
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


def test_schema_quiz_uses_top_level_quiz_en_quiz_ko():
    """Parser reads data.get('quiz_en') — schema must not nest under 'quiz'."""
    schema = build_news_writer_json_schema(["https://a.com"])
    props = schema["schema"]["properties"]
    assert "quiz_en" in props
    assert "quiz_ko" in props
    assert "quiz" not in props
    assert set(schema["schema"]["required"]) >= {"quiz_en", "quiz_ko"}


def test_schema_quiz_fields_match_parser_contract():
    """Fields must be question/answer/options/explanation (not q/a)."""
    schema = build_news_writer_json_schema(["https://a.com"])
    quiz_props = schema["schema"]["properties"]["quiz_en"]["properties"]
    assert set(quiz_props) == {"question", "answer", "options", "explanation"}

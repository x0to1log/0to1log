"""Pydantic + JSON schema for news writer strict output.

The OpenAI ``response_format={"type": "json_schema", "strict": true, ...}``
mode rejects responses where ``citations[].url`` is not in the enum — that
enum is built from the fact_pack allowlist. Body text references citations
by ``[CITE_N]`` placeholder rather than inline ``[N](URL)``; substitution
happens in ``services.agents.citation_substitution``.

Quiz contract: ``quiz_en`` and ``quiz_ko`` are separate top-level fields
matching the existing parser (``pipeline_digest.py`` line 764+ reads
``data.get("quiz_en")`` / ``data.get("quiz_ko")``). Writer emits
``answer_index`` (integer 0-3) instead of ``answer`` text — strict
json_schema enforces the range, eliminating the silent-drop class of
bug where verbatim string match failed (Apr 26 KO quiz_poll_expert
incident). The validator
(``pipeline._validate_and_shuffle_quiz_item``) resolves the index to
text before saving, so the DB-facing
``guide_items.quiz_poll_{persona}`` shape (``question / answer /
options / explanation``) stays unchanged.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class Citation(BaseModel):
    n: int = Field(ge=1, le=50)
    url: str = Field(min_length=1)

    @field_validator("url")
    @classmethod
    def url_must_be_http(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("url must start with http(s)://")
        return v


class QuizOneLocale(BaseModel):
    question: str
    answer_index: int = Field(ge=0, le=3)
    options: list[str] = Field(min_length=4, max_length=4)
    explanation: str = ""

    @field_validator("answer_index", mode="before")
    @classmethod
    def reject_bool(cls, v: Any) -> Any:
        # isinstance(True, int) is True in Python. Pydantic v2 default
        # mode coerces bool -> int silently, which would map True/False
        # to options[1]/options[0]. Reject explicitly.
        if isinstance(v, bool):
            raise ValueError("answer_index must be an integer, not a bool")
        return v


class SourceEntry(BaseModel):
    """Writer-supplied source card metadata.

    Post-processing (``pipeline_digest._fill_source_titles``) merges this
    with the URLs extracted from body citations to produce the final
    source_cards saved to DB. Without writer-supplied ``title``, the
    frontend falls back to the URL hostname, producing ugly labels like
    "Arunbaby" for arunbaby.com.
    """

    id: int = Field(ge=1, le=50)
    url: str = Field(min_length=1)
    title: str = ""


class NewsWriterOutput(BaseModel):
    headline: str
    headline_ko: str
    excerpt: str
    excerpt_ko: str
    en: str
    ko: str
    citations: list[Citation]
    tags: list[str]
    focus_items: list[str]
    focus_items_ko: list[str]
    quiz_en: QuizOneLocale
    quiz_ko: QuizOneLocale
    sources: list[SourceEntry]


def build_news_writer_json_schema(allowlist_urls: list[str]) -> dict[str, Any]:
    """Build an OpenAI strict json_schema with citations[].url as an enum.

    The writer cannot emit a URL that is not in ``allowlist_urls`` — the API
    rejects the response at the schema-validation step (up to 2 internal
    retries, then ``BadRequestError``).
    """
    if not allowlist_urls:
        raise ValueError(
            "Cannot build writer schema with empty allowlist — "
            "fact_pack.news_items must have at least one URL."
        )

    seen: set[str] = set()
    unique: list[str] = []
    for url in allowlist_urls:
        if url not in seen:
            seen.add(url)
            unique.append(url)

    return {
        "name": "news_writer_output",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "headline", "headline_ko", "excerpt", "excerpt_ko",
                "en", "ko", "citations",
                "tags", "focus_items", "focus_items_ko",
                "quiz_en", "quiz_ko",
                "sources",
            ],
            "properties": {
                "headline": {"type": "string"},
                "headline_ko": {"type": "string"},
                "excerpt": {"type": "string"},
                "excerpt_ko": {"type": "string"},
                "en": {"type": "string"},
                "ko": {"type": "string"},
                "citations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["n", "url"],
                        "properties": {
                            "n": {"type": "integer", "minimum": 1, "maximum": 50},
                            "url": {"type": "string", "enum": unique},
                        },
                    },
                },
                "tags": {"type": "array", "items": {"type": "string"}},
                "focus_items": {"type": "array", "items": {"type": "string"}},
                "focus_items_ko": {"type": "array", "items": {"type": "string"}},
                "quiz_en": _quiz_locale_schema(),
                "quiz_ko": _quiz_locale_schema(),
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["id", "url", "title"],
                        "properties": {
                            "id": {"type": "integer", "minimum": 1, "maximum": 50},
                            "url": {"type": "string"},
                            "title": {"type": "string"},
                        },
                    },
                },
            },
        },
    }


def _quiz_locale_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        # `explanation` is required by strict schema (OpenAI strict mode
        # requires all properties to be required), but writer can emit "".
        "required": ["question", "answer_index", "options", "explanation"],
        "properties": {
            "question": {"type": "string"},
            "answer_index": {
                "type": "integer",
                "minimum": 0,
                "maximum": 3,
            },
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 4,
                "maxItems": 4,
            },
            "explanation": {"type": "string"},
        },
    }

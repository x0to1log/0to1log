"""Tests for [CITE_N] → [N](URL) substitution."""
import pytest

from services.agents.citation_substitution import (
    apply_citations,
    CitationSubstitutionError,
)


def test_simple_substitution():
    body = "Foo launched [CITE_1] today."
    citations = [{"n": 1, "url": "https://example.com/a"}]
    out = apply_citations(body, citations)
    assert out == "Foo launched [1](https://example.com/a) today."


def test_multiple_placeholders_same_citation():
    body = "A [CITE_1] and B [CITE_1]."
    citations = [{"n": 1, "url": "https://a.com"}]
    out = apply_citations(body, citations)
    assert out == "A [1](https://a.com) and B [1](https://a.com)."


def test_multiple_distinct_citations():
    body = "[CITE_1] then [CITE_2] then [CITE_3]."
    citations = [
        {"n": 1, "url": "https://a.com"},
        {"n": 2, "url": "https://b.com"},
        {"n": 3, "url": "https://c.com"},
    ]
    out = apply_citations(body, citations)
    assert "[1](https://a.com)" in out
    assert "[2](https://b.com)" in out
    assert "[3](https://c.com)" in out


def test_missing_citation_raises():
    body = "See [CITE_5]."
    citations = [{"n": 1, "url": "https://a.com"}]
    with pytest.raises(CitationSubstitutionError) as exc:
        apply_citations(body, citations)
    assert "5" in str(exc.value)


def test_unused_citation_is_ignored():
    body = "No placeholder here."
    citations = [{"n": 1, "url": "https://a.com"}]
    out = apply_citations(body, citations)
    assert out == "No placeholder here."


def test_no_citations_no_placeholders():
    assert apply_citations("plain text", []) == "plain text"


def test_empty_body_returns_empty():
    assert apply_citations("", []) == ""


def test_lone_inline_url_in_body_raises():
    body = "Oops [1](https://rogue.com) here."
    with pytest.raises(CitationSubstitutionError) as exc:
        apply_citations(body, [])
    assert "inline" in str(exc.value).lower()

"""Tests for _inject_cp_citations — post-processing that linkifies
`> — Hacker News` attribution lines in the Community Pulse section."""

from unittest.mock import MagicMock


def _make_insight(*, url: str, source_label: str):
    insight = MagicMock()
    insight.url = url
    insight.source_label = source_label
    return insight


def test_inject_cp_citations_linkifies_single_hn_block_en():
    from services.pipeline import _inject_cp_citations

    body = """## Big Tech

Some story content.

## Community Pulse

**Hacker News** (1,203↑) — Mixed sentiment about design handoff.

> "how do you hand over to claude code exactly?"
> — Hacker News

> "figma will lose users like me"
> — Hacker News

## Connecting the Dots

Closing thoughts.
"""
    cmap = {
        "https://news.ycombinator.com/item?id=ABC": _make_insight(
            url="https://news.ycombinator.com/item?id=ABC",
            source_label="Hacker News",
        )
    }
    out = _inject_cp_citations(body, cmap)

    # Both attribution lines in the HN block linkify to the same URL
    expected_link = "> — [Hacker News](https://news.ycombinator.com/item?id=ABC)"
    assert out.count(expected_link) == 2, f"expected 2 linkified attributions, got {out.count(expected_link)}"
    # Original `> — Hacker News` (without link) must be gone
    assert "> — Hacker News\n" not in out
    # Non-CP content untouched
    assert "Some story content." in out
    assert "Closing thoughts." in out


def test_inject_cp_citations_linkifies_ko_header():
    from services.pipeline import _inject_cp_citations

    body = """## 커뮤니티 반응

**Hacker News** (1,203↑) — 혼재된 반응.

> "간단한 질문인데"
> — Hacker News
"""
    cmap = {
        "https://news.ycombinator.com/item?id=XYZ": _make_insight(
            url="https://news.ycombinator.com/item?id=XYZ",
            source_label="Hacker News",
        )
    }
    out = _inject_cp_citations(body, cmap)
    assert "> — [Hacker News](https://news.ycombinator.com/item?id=XYZ)" in out
    assert "> — Hacker News\n" not in out


def test_inject_cp_citations_multiple_blocks_assigns_urls_positionally():
    """Two **r/OpenAI** blocks in the same CP section get different URLs,
    matched by insertion order in community_summary_map."""
    from services.pipeline import _inject_cp_citations

    body = """## Community Pulse

**r/OpenAI** (500↑) — discussion one.

> "first quote"
> — r/OpenAI

**r/OpenAI** (200↑) — discussion two.

> "second quote"
> — r/OpenAI
"""
    cmap = {
        "https://reddit.com/r/OpenAI/comments/first": _make_insight(
            url="https://reddit.com/r/OpenAI/comments/first",
            source_label="r/OpenAI",
        ),
        "https://reddit.com/r/OpenAI/comments/second": _make_insight(
            url="https://reddit.com/r/OpenAI/comments/second",
            source_label="r/OpenAI",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    assert "> — [r/OpenAI](https://reddit.com/r/OpenAI/comments/first)" in out
    assert "> — [r/OpenAI](https://reddit.com/r/OpenAI/comments/second)" in out


def test_inject_cp_citations_preserves_non_cp_blockquotes():
    """Blockquotes OUTSIDE the CP section (e.g., direct source quotes in Big Tech)
    must NOT be modified, even if attribution line matches the pattern."""
    from services.pipeline import _inject_cp_citations

    body = """## Big Tech

### OpenAI ships new model

OpenAI announced something.

> "a direct quote from a primary source"
> — Hacker News

More analysis.

## Community Pulse

**Hacker News** (100↑) — Sentiment.

> "community reaction"
> — Hacker News
"""
    cmap = {
        "https://news.ycombinator.com/item?id=CP": _make_insight(
            url="https://news.ycombinator.com/item?id=CP",
            source_label="Hacker News",
        )
    }
    out = _inject_cp_citations(body, cmap)
    # Non-CP blockquote preserved verbatim (still has `> — Hacker News` without link)
    assert "> — Hacker News\n\nMore analysis." in out
    # CP blockquote linkified
    assert "> — [Hacker News](https://news.ycombinator.com/item?id=CP)" in out


def test_inject_cp_citations_empty_map_returns_unchanged():
    from services.pipeline import _inject_cp_citations

    body = """## Community Pulse

**Hacker News** (100↑) — Mixed.

> "quote"
> — Hacker News
"""
    out = _inject_cp_citations(body, {})
    assert out == body


def test_inject_cp_citations_no_cp_section_returns_unchanged():
    from services.pipeline import _inject_cp_citations

    body = """## Big Tech

A story without CP.
"""
    cmap = {
        "https://example.com/x": _make_insight(url="https://example.com/x", source_label="Hacker News")
    }
    out = _inject_cp_citations(body, cmap)
    assert out == body


def test_inject_cp_citations_unmatched_label_leaves_attribution_untouched():
    """If the body references a source_label we don't have in the map,
    the attribution stays as-is (graceful degradation)."""
    from services.pipeline import _inject_cp_citations

    body = """## Community Pulse

**TwitterX** (50↑) — sentiment.

> "quote"
> — TwitterX
"""
    cmap = {
        "https://news.ycombinator.com/item?id=HN": _make_insight(
            url="https://news.ycombinator.com/item?id=HN",
            source_label="Hacker News",  # different label
        )
    }
    out = _inject_cp_citations(body, cmap)
    assert "> — TwitterX\n" in out
    assert "[TwitterX]" not in out

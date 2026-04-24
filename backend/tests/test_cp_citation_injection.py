"""Tests for _inject_cp_citations — post-processing that linkifies
`> — Hacker News` / `> — r/xxx` attribution lines in the Community Pulse
section using per-insight thread URLs matched by upvote count."""

from models.news_pipeline import CommunityInsight


def _make_insight(*, source_label: str, hn_url: str | None = None, reddit_url: str | None = None):
    return CommunityInsight(
        source_label=source_label,
        hn_url=hn_url,
        reddit_url=reddit_url,
    )


def test_inject_linkifies_hn_block_using_insight_hn_url():
    from services.pipeline import _inject_cp_citations

    body = """## Community Pulse

**Hacker News** (79↑) — Skeptical.

> "first"
> — Hacker News

> "second"
> — Hacker News
"""
    cmap = {
        "https://arxiv.org/abs/ANY": _make_insight(
            source_label="Hacker News 79↑ · 116 comments",
            hn_url="https://news.ycombinator.com/item?id=42",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    # Both attributions linkify to the THREAD URL (not arxiv)
    link = "> — [Hacker News](https://news.ycombinator.com/item?id=42)"
    assert out.count(link) == 2
    assert "> — Hacker News\n" not in out


def test_inject_matches_multiple_hn_blocks_by_upvote_count():
    """Regression for Apr 21 positional bug: two HN blocks at different upvote
    counts must each get their OWN thread URL, regardless of dict order."""
    from services.pipeline import _inject_cp_citations

    # Deliberately insert the 58-upvote insight FIRST in the dict —
    # writer put the 79 block first in body. Matching by upvote count should
    # still pair (79 block, insight with "Hacker News 79↑...") correctly.
    cmap = {
        "https://arxiv.org/abs/LOWER": _make_insight(
            source_label="Hacker News 58↑ · 34 comments",
            hn_url="https://news.ycombinator.com/item?id=58",
        ),
        "https://arxiv.org/abs/HIGHER": _make_insight(
            source_label="Hacker News 79↑ · 116 comments",
            hn_url="https://news.ycombinator.com/item?id=79",
        ),
    }
    body = """## Community Pulse

**Hacker News** (79↑) — High-upvote discussion.

> "popular"
> — Hacker News

**Hacker News** (58↑) — Smaller discussion.

> "niche"
> — Hacker News
"""
    out = _inject_cp_citations(body, cmap)
    # 79 block → id=79 URL; 58 block → id=58 URL
    assert "> — [Hacker News](https://news.ycombinator.com/item?id=79)" in out
    assert "> — [Hacker News](https://news.ycombinator.com/item?id=58)" in out


def test_inject_linkifies_reddit_block_using_insight_reddit_url():
    from services.pipeline import _inject_cp_citations

    body = """## Community Pulse

**r/OpenAI** (500↑) — sentiment.

> "reaction"
> — r/OpenAI
"""
    cmap = {
        "https://example.com/PRIMARY": _make_insight(
            source_label="r/OpenAI (500↑)",
            reddit_url="https://www.reddit.com/r/OpenAI/comments/abc/t/",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    assert "> — [r/OpenAI](https://www.reddit.com/r/OpenAI/comments/abc/t/)" in out


def test_inject_handles_ko_header():
    from services.pipeline import _inject_cp_citations

    body = """## 커뮤니티 반응

**Hacker News** (79↑) — 혼재된 반응.

> "간단한 질문"
> — Hacker News
"""
    cmap = {
        "https://arxiv.org/abs/X": _make_insight(
            source_label="Hacker News 79↑ · 116 comments",
            hn_url="https://news.ycombinator.com/item?id=42",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    assert "> — [Hacker News](https://news.ycombinator.com/item?id=42)" in out


def test_inject_unmatched_upvote_count_leaves_attribution_untouched():
    """If no insight has matching upvote count, the attribution stays raw."""
    from services.pipeline import _inject_cp_citations

    body = """## Community Pulse

**Hacker News** (999↑) — orphan block.

> "quote"
> — Hacker News
"""
    cmap = {
        "https://arxiv.org/abs/X": _make_insight(
            source_label="Hacker News 50↑ · 10 comments",
            hn_url="https://news.ycombinator.com/item?id=50",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    assert "> — Hacker News\n" in out
    assert "[Hacker News]" not in out


def test_inject_missing_hn_url_leaves_attribution_untouched():
    """If insight matches by upvote count but has no hn_url, leave alone."""
    from services.pipeline import _inject_cp_citations

    body = """## Community Pulse

**Hacker News** (79↑) — old checkpoint.

> "quote"
> — Hacker News
"""
    cmap = {
        "https://arxiv.org/abs/X": _make_insight(
            source_label="Hacker News 79↑ · 116 comments",
            hn_url=None,  # old checkpoint pre-URL-plumbing
        ),
    }
    out = _inject_cp_citations(body, cmap)
    assert "> — Hacker News\n" in out


def test_inject_empty_map_returns_unchanged():
    from services.pipeline import _inject_cp_citations

    body = "## Community Pulse\n\n**Hacker News** (79↑) — foo.\n\n> q\n> — Hacker News\n"
    out = _inject_cp_citations(body, {})
    assert out == body


def test_inject_no_cp_section_returns_unchanged():
    from services.pipeline import _inject_cp_citations

    body = "## Big Tech\n\nStory without CP.\n"
    cmap = {
        "https://arxiv.org/abs/X": _make_insight(
            source_label="Hacker News 79↑",
            hn_url="https://news.ycombinator.com/item?id=42",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    assert out == body


def test_inject_preserves_non_cp_blockquotes():
    """Blockquotes outside the CP section (e.g., direct primary-source quotes
    in Big Tech) must not be touched even if they use `> — Label`."""
    from services.pipeline import _inject_cp_citations

    body = """## Big Tech

### OpenAI ships model

> "primary-source quote"
> — Hacker News

## Community Pulse

**Hacker News** (79↑) — community.

> "community quote"
> — Hacker News
"""
    cmap = {
        "https://arxiv.org/abs/X": _make_insight(
            source_label="Hacker News 79↑",
            hn_url="https://news.ycombinator.com/item?id=42",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    # Pre-CP blockquote unchanged
    assert "> — Hacker News\n\n## Community Pulse" in out
    # CP blockquote linkified
    assert "> — [Hacker News](https://news.ycombinator.com/item?id=42)\n" in out


def test_inject_linkifies_bare_block_header():
    """When writer emits a bare `**Hacker News** (79↑)` header (didn't follow
    the new contract), post-processor should linkify the header using the
    matched insight's hn_url."""
    from services.pipeline import _inject_cp_citations
    from models.news_pipeline import CommunityInsight

    body = """## Community Pulse

**Hacker News** (79↑) — discussion summary.

> "quote over ten chars"
> — Hacker News
"""
    cmap = {
        "https://arxiv.org/abs/X": CommunityInsight(
            source_label="Hacker News 79↑ · 116 comments",
            hn_url="https://news.ycombinator.com/item?id=42",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    assert "**[Hacker News](https://news.ycombinator.com/item?id=42)** (79↑)" in out
    assert "> — [Hacker News](https://news.ycombinator.com/item?id=42)" in out


def test_inject_linkifies_bare_reddit_block_header():
    from services.pipeline import _inject_cp_citations
    from models.news_pipeline import CommunityInsight

    body = """## Community Pulse

**r/OpenAI** (500↑) — sentiment.

> "quote over ten chars"
> — r/OpenAI
"""
    cmap = {
        "https://example.com/X": CommunityInsight(
            source_label="r/OpenAI (500↑)",
            reddit_url="https://www.reddit.com/r/OpenAI/comments/abc/t/",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    assert "**[r/OpenAI](https://www.reddit.com/r/OpenAI/comments/abc/t/)** (500↑)" in out


def test_inject_is_idempotent_on_already_linked_block_header():
    """Writer followed the new contract — block header already has
    [Label](URL). Post-processor must NOT double-link or otherwise
    corrupt the output."""
    from services.pipeline import _inject_cp_citations
    from models.news_pipeline import CommunityInsight

    original = """## Community Pulse

**[Hacker News](https://news.ycombinator.com/item?id=42)** (79↑) — discussion.

> "quote over ten chars"
> — [Hacker News](https://news.ycombinator.com/item?id=42)
"""
    cmap = {
        "https://arxiv.org/abs/X": CommunityInsight(
            source_label="Hacker News 79↑ · 116 comments",
            hn_url="https://news.ycombinator.com/item?id=42",
        ),
    }
    out = _inject_cp_citations(original, cmap)
    assert out == original
    # Specifically: no double link like [[Hacker News](...)](...)
    assert "[[" not in out
    assert "]]" not in out


def test_inject_is_idempotent_on_already_linked_attribution():
    """Attribution already linked — post-processor must not touch it.
    Meanwhile a bare attribution in the same block DOES get linkified."""
    from services.pipeline import _inject_cp_citations
    from models.news_pipeline import CommunityInsight

    body = """## Community Pulse

**[Hacker News](https://news.ycombinator.com/item?id=42)** (79↑) — discussion.

> "quote A over ten chars"
> — [Hacker News](https://news.ycombinator.com/item?id=42)

> "quote B over ten chars"
> — Hacker News
"""
    cmap = {
        "https://arxiv.org/abs/X": CommunityInsight(
            source_label="Hacker News 79↑ · 116 comments",
            hn_url="https://news.ycombinator.com/item?id=42",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    linked_attr_count = out.count("> — [Hacker News](https://news.ycombinator.com/item?id=42)")
    assert linked_attr_count == 2, f"expected 2 linked attributions, got {linked_attr_count}"
    # No double-linking
    assert "[[" not in out


def test_inject_handles_partial_writer_compliance():
    """Writer linked attribution but forgot block header — post-processor
    should still linkify the block header."""
    from services.pipeline import _inject_cp_citations
    from models.news_pipeline import CommunityInsight

    body = """## Community Pulse

**Hacker News** (79↑) — discussion.

> "quote over ten chars"
> — [Hacker News](https://news.ycombinator.com/item?id=42)
"""
    cmap = {
        "https://arxiv.org/abs/X": CommunityInsight(
            source_label="Hacker News 79↑",
            hn_url="https://news.ycombinator.com/item?id=42",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    assert "**[Hacker News](https://news.ycombinator.com/item?id=42)** (79↑)" in out
    # Attribution stays linked (not double-linked)
    assert out.count("> — [Hacker News](https://news.ycombinator.com/item?id=42)") == 1


def test_inject_case1_overrides_writer_url_when_mismatched_with_index():
    """If writer emits a linked block header with a URL that doesn't match
    the insight's hn_url for the same upvote count, the post-processor
    must override the writer's URL with the authoritative insight URL.
    This prevents silent corruption from LLM typos or hallucinations.

    Simpler-scope approach (header-only): only the block header is rewritten.
    An already-linked attribution with the wrong URL is left alone (deferred
    scope — see code comment in Case 1).  A bare attribution DOES pick up the
    corrected current_url from the overridden header."""
    from services.pipeline import _inject_cp_citations
    from models.news_pipeline import CommunityInsight

    body = """## Community Pulse

**[Hacker News](https://news.ycombinator.com/item?id=WRONG)** (79↑) — discussion.

> "quote A over ten chars"
> — [Hacker News](https://news.ycombinator.com/item?id=WRONG)

> "quote B over ten chars"
> — Hacker News
"""
    cmap = {
        "https://arxiv.org/abs/X": CommunityInsight(
            source_label="Hacker News 79↑ · 116 comments",
            hn_url="https://news.ycombinator.com/item?id=42",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    # Header's wrong URL rewritten to authoritative URL
    assert "**[Hacker News](https://news.ycombinator.com/item?id=42)** (79↑)" in out
    # Bare attribution (quote B) picks up the corrected current_url
    assert "> — [Hacker News](https://news.ycombinator.com/item?id=42)" in out
    # Quote A's attribution (already-linked, wrong URL) is left alone — deferred scope
    assert "> — [Hacker News](https://news.ycombinator.com/item?id=WRONG)" in out


def test_inject_case1_keeps_writer_url_when_matches_index():
    """If writer-emitted URL matches the insight's authoritative URL,
    no override — the line passes through unchanged (idempotency)."""
    from services.pipeline import _inject_cp_citations
    from models.news_pipeline import CommunityInsight

    body = """## Community Pulse

**[Hacker News](https://news.ycombinator.com/item?id=42)** (79↑) — discussion.

> "quote over ten chars"
> — [Hacker News](https://news.ycombinator.com/item?id=42)
"""
    cmap = {
        "https://arxiv.org/abs/X": CommunityInsight(
            source_label="Hacker News 79↑ · 116 comments",
            hn_url="https://news.ycombinator.com/item?id=42",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    # No rewrites — URL already matches
    assert out == body

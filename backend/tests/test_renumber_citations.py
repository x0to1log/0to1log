"""_renumber_citations preserves CP linkifier output.

Background (2026-04-26 incident, post bold-paren-abbrev fix):
After fixing the bold-paren regex to preserve `**[Hacker News](URL)**`,
a SECOND bug surfaced: _renumber_citations' placeholder-recovery path
matched any `[<non-digit>](URL)` pattern — including legitimate
markdown link labels like `[Hacker News]`. The bug had two failure
modes depending on the URL allowlist:
  - URL in allowlist  → label rewritten to digit: `[5](URL)` (label lost)
  - URL not in allowlist → entire link stripped: `` (label + URL lost)
The Apr 26 saved CP blocks showed `**** (805↑) — ...` — both label
and URL gone — because the post-write `allowed_urls` did not include
CP thread URLs.

Fix: tighten placeholder_re to match only placeholder-shaped labels
(CITE, CITE_N, N, CITATION_N variants), leaving descriptive markdown
link labels alone.
"""
from services.pipeline import _renumber_citations


class TestPlaceholderRecovery:
    """Cases the recovery SHOULD touch — actual placeholder literals."""

    def test_cite_underscore_n_recovered(self):
        body = "See [CITE_1](https://example.com) for details."
        out, cards = _renumber_citations(body, allowed_urls={"https://example.com"})
        assert out == "See [1](https://example.com) for details."
        assert cards[0]["url"] == "https://example.com"

    def test_lowercase_cite_recovered(self):
        body = "[cite_2](https://a.com)"
        out, _ = _renumber_citations(body, allowed_urls={"https://a.com"})
        assert out == "[1](https://a.com)"

    def test_bare_n_placeholder_recovered(self):
        body = "[N](https://b.com)"
        out, _ = _renumber_citations(body, allowed_urls={"https://b.com"})
        assert out == "[1](https://b.com)"


class TestMarkdownLinkLabelsPreserved:
    """Descriptive markdown link labels MUST be preserved verbatim."""

    def test_hn_block_header_preserved_when_url_allowed(self):
        url = "https://news.ycombinator.com/item?id=47892074"
        body = f"**[Hacker News]({url})** (805↑) — discussion."
        out, _ = _renumber_citations(body, allowed_urls={url})
        assert out == body

    def test_reddit_subreddit_label_preserved(self):
        url = "https://reddit.com/r/MachineLearning/comments/abc"
        body = f"**[r/MachineLearning]({url})** (250↑) — debate."
        out, _ = _renumber_citations(body, allowed_urls={url})
        assert out == body

    def test_link_with_digit_only_label_renumbered(self):
        """Existing behavior: [N](URL) IS renumbered. Sanity check."""
        body = "Foo [3](https://x.com) bar."
        out, cards = _renumber_citations(body, allowed_urls={"https://x.com"})
        assert "[1](https://x.com)" in out
        assert cards[0]["url"] == "https://x.com"


class TestStripping:
    """Hallucinated URLs (not in allowlist) get stripped — but only for
    placeholder-shaped labels, never for descriptive link labels."""

    def test_unknown_url_with_placeholder_stripped(self):
        body = "Suspicious [CITE_5](https://hallucinated.fake) here."
        out, _ = _renumber_citations(body, allowed_urls={"https://real.com"})
        assert "[CITE_5]" not in out
        assert "hallucinated.fake" not in out

    def test_unknown_url_with_descriptive_label_preserved(self):
        """If we can't trust the URL, that's a problem — but the descriptive
        label is meaningful and should not be wiped out as collateral.
        Current implementation leaves both intact (URL is shown to readers
        who can judge for themselves)."""
        body = "**[Hacker News](https://possibly.bad.com)** (100↑)"
        out, _ = _renumber_citations(body, allowed_urls={"https://real.com"})
        assert out == body

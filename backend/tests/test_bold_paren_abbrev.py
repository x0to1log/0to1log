r"""_fix_bold_paren_abbrev — separates inline abbreviations without breaking links.

Background (2026-04-26 incident):
The post-process at pipeline_digest.py:1389-1391 originally used a regex
`\*\*([^*]+?)\(([^)]+)\)\*\*` that matched both
- `**Rejection Fine-Tuning(RFT)**` (intended) and
- `**[Hacker News](https://...)**` (UNINTENDED — markdown links).

The unintended match destroyed CP block linkifier output, producing the
broken split form `**[Hacker News]** (https://...)` that rendered as
unlinked text. Helper now scopes the rewrite to the abbreviation case
only.
"""
from services.pipeline import _fix_bold_paren_abbrev


class TestAbbrevPositive:
    """Cases the helper SHOULD rewrite."""

    def test_simple_abbrev_separated(self):
        out = _fix_bold_paren_abbrev("**Rejection Fine-Tuning(RFT)**")
        assert out == "**Rejection Fine-Tuning** (RFT)"

    def test_abbrev_with_spaces_in_name(self):
        out = _fix_bold_paren_abbrev("**Large Language Model(LLM)**")
        assert out == "**Large Language Model** (LLM)"

    def test_multiple_abbrevs_in_text(self):
        text = "Use **Foo Bar(FB)** and **Baz Qux(BQ)** together."
        out = _fix_bold_paren_abbrev(text)
        assert out == "Use **Foo Bar** (FB) and **Baz Qux** (BQ) together."


class TestMarkdownLinkPreserved:
    """Cases the helper MUST NOT touch — these are markdown links."""

    def test_hn_block_header_preserved(self):
        link = "**[Hacker News](https://news.ycombinator.com/item?id=47892074)**"
        assert _fix_bold_paren_abbrev(link) == link

    def test_reddit_block_header_preserved(self):
        link = "**[r/MachineLearning](https://reddit.com/r/MachineLearning/comments/abc123)**"
        assert _fix_bold_paren_abbrev(link) == link

    def test_linked_header_in_full_cp_line_preserved(self):
        line = "**[Hacker News](https://news.ycombinator.com/item?id=47892074)** (805↑) — mixed sentiment"
        assert _fix_bold_paren_abbrev(line) == line

    def test_http_link_also_preserved(self):
        link = "**[Example](http://example.com/path)**"
        assert _fix_bold_paren_abbrev(link) == link


class TestMixed:
    """Real-world digest content combining both patterns."""

    def test_abbrev_and_link_in_same_text(self):
        text = (
            "Background on **Rejection Fine-Tuning(RFT)**.\n\n"
            "## Community Pulse\n\n"
            "**[Hacker News](https://news.ycombinator.com/item?id=47892074)** (805↑) — discussion."
        )
        expected = (
            "Background on **Rejection Fine-Tuning** (RFT).\n\n"
            "## Community Pulse\n\n"
            "**[Hacker News](https://news.ycombinator.com/item?id=47892074)** (805↑) — discussion."
        )
        assert _fix_bold_paren_abbrev(text) == expected

    def test_idempotent_on_already_separated(self):
        text = "**Rejection Fine-Tuning** (RFT)"
        assert _fix_bold_paren_abbrev(text) == text

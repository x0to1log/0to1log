"""Voice normalization in HN comment scraper.

Algolia's `comment_text` for a single comment can contain
HN's `> ` quote-of-other-comment convention followed by the
author's own reply. Both get HTML-stripped together, fusing
two voices into one string. Downstream summarizer treats it
as one voice → quote pollution (Apr 26 'Who are you quoting?'
incident on HN thread 47892074).

Fix: strip lines starting with `>` (after lstrip) before the
length / spam gates. After stripping, meta-only replies
(`Who are you quoting?`, `+1`, `exactly`) fall below the
50-char gate and self-drop.
"""
import re
import html as _html


def _clean_hn_comment(text: str) -> str:
    """Mirror of the scraper transform under test.

    Keep this in sync with the implementation in
    backend/services/news_collection.py.
    """
    clean = re.sub(r"<[^>]+>", " ", text).strip()
    clean = _html.unescape(clean)
    lines = [ln for ln in clean.splitlines() if not ln.lstrip().startswith(">")]
    clean = " ".join(lines)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


class TestHNVoiceNormalization:
    def test_quoted_line_stripped(self):
        text = "<p>&gt; Original quoted text from another comment\n<p>Who are you quoting?"
        out = _clean_hn_comment(text)
        assert "Original quoted text" not in out
        assert out == "Who are you quoting?"

    def test_meta_only_reply_falls_below_length_gate(self):
        # After stripping the > line, only "Who are you quoting?" (21 chars) remains.
        # Caller's `len(clean) > 50` gate will drop it — assert length here.
        text = "<p>&gt; Some quoted opinion from another HN user about $40B\n<p>Who are you quoting?"
        out = _clean_hn_comment(text)
        assert len(out) <= 50  # would be dropped by caller

    def test_pure_author_voice_preserved(self):
        text = "<p>This is my own analysis with no quoting. " * 3
        out = _clean_hn_comment(text)
        assert "my own analysis" in out
        assert ">" not in out

    def test_multiple_quote_lines_stripped(self):
        text = "<p>&gt; Quote line one\n<p>&gt; Quote line two\n<p>My actual reply here, long enough to pass length filter for sure okay."
        out = _clean_hn_comment(text)
        assert "Quote line" not in out
        assert "My actual reply" in out

    def test_indented_quote_line_stripped(self):
        text = "<p>   &gt; Indented quote\n<p>Reply text that is genuinely long enough to clear the 50 char threshold."
        out = _clean_hn_comment(text)
        assert "Indented quote" not in out
        assert "Reply text" in out

    def test_inline_gt_not_stripped(self):
        # `>` mid-sentence (e.g. "5 > 3") is NOT a line-leading quote marker
        text = "<p>The benchmark shows 5 > 3 in latency for this model on the new hardware."
        out = _clean_hn_comment(text)
        assert "5 > 3" in out


class TestScraperConsistency:
    def test_module_imports(self):
        # Smoke check that the scraper module is importable and HN_COMMENTS_TOP_N is unchanged.
        from services.news_collection import HN_COMMENTS_TOP_N
        assert HN_COMMENTS_TOP_N == 30

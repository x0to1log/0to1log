"""Tests for _parse_source_meta — extracts source_label + thread URLs
from community text blobs (both new-format with url= tokens and old-format
without, for backward compatibility)."""


def test_parse_hn_only_with_url():
    from services.agents.ranking import _parse_source_meta

    raw = (
        "[Hacker News|url=https://news.ycombinator.com/item?id=12345] "
        "Title | 79 points | 116 comments\n"
        "Top comments:\n"
        '> "first"\n'
    )
    label, hn_url, reddit_url = _parse_source_meta(raw)
    assert label == "Hacker News 79↑ · 116 comments"
    assert hn_url == "https://news.ycombinator.com/item?id=12345"
    assert reddit_url is None


def test_parse_reddit_only_with_url():
    from services.agents.ranking import _parse_source_meta

    raw = (
        "[Reddit r/OpenAI|url=https://www.reddit.com/r/OpenAI/comments/abc/t/] "
        "Title | 500 upvotes | 120 comments\n"
    )
    label, hn_url, reddit_url = _parse_source_meta(raw)
    assert label == "r/OpenAI (500↑)"
    assert hn_url is None
    assert reddit_url == "https://www.reddit.com/r/OpenAI/comments/abc/t/"


def test_parse_both_hn_and_reddit_with_urls():
    from services.agents.ranking import _parse_source_meta

    raw = (
        "[Hacker News|url=https://news.ycombinator.com/item?id=1] HNTitle | 50 points | 10 comments\n"
        "Top comments:\n> \"hn\"\n\n"
        "[Reddit r/AI|url=https://www.reddit.com/r/AI/comments/x/t/] RdTitle | 100 upvotes | 20 comments\n"
    )
    label, hn_url, reddit_url = _parse_source_meta(raw)
    assert label == "Hacker News 50↑ · 10 comments · r/AI (100↑)"
    assert hn_url == "https://news.ycombinator.com/item?id=1"
    assert reddit_url == "https://www.reddit.com/r/AI/comments/x/t/"


def test_parse_backcompat_no_url_tokens():
    """Old blobs without url= still produce the label and return None for URLs."""
    from services.agents.ranking import _parse_source_meta

    raw = "[Hacker News] Title | 79 points | 116 comments\nTop comments:\n"
    label, hn_url, reddit_url = _parse_source_meta(raw)
    assert label == "Hacker News 79↑ · 116 comments"
    assert hn_url is None
    assert reddit_url is None


def test_parse_empty_blob():
    from services.agents.ranking import _parse_source_meta

    label, hn_url, reddit_url = _parse_source_meta("")
    assert label == ""
    assert hn_url is None
    assert reddit_url is None

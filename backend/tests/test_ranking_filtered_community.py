"""Tests for the pre-ranking filter that drops community_map entries
whose summarizer marked the thread as irrelevant (sentiment=null).
Without this filter, irrelevant high-upvote threads influence Lead/Supporting
ranking via their upvote counts."""

from models.news_pipeline import CommunityInsight, ThreadInfo


def test_filter_drops_null_sentiment_entries():
    from services.pipeline import _filter_community_map_by_summary

    community_map = {
        "https://a.example.com/story": "HN thread blob A with 500 upvotes",
        "https://b.example.com/story": "HN thread blob B with 1000 upvotes",
        "https://c.example.com/story": "HN thread blob C with 50 upvotes",
    }
    # Use model_construct to bypass pydantic validation and create instance with sentiment=None
    community_summary_map = {
        "https://a.example.com/story": CommunityInsight(sentiment="mixed", source_label="HN 500↑"),
        "https://b.example.com/story": CommunityInsight.model_construct(sentiment=None, source_label="HN 1000↑"),  # off-topic
        "https://c.example.com/story": CommunityInsight(sentiment="negative", source_label="HN 50↑"),
    }
    filtered = _filter_community_map_by_summary(community_map, community_summary_map)
    assert "https://a.example.com/story" in filtered
    assert "https://c.example.com/story" in filtered
    # Irrelevant thread excluded
    assert "https://b.example.com/story" not in filtered


def test_filter_drops_entries_with_no_insight():
    """If the summarizer produced no insight for a URL (mapping missing),
    treat it as unclassified and exclude — same as sentiment=null."""
    from services.pipeline import _filter_community_map_by_summary

    community_map = {
        "https://a.example.com/story": "blob A",
        "https://missing.example.com/story": "blob without insight",
    }
    community_summary_map = {
        "https://a.example.com/story": CommunityInsight(sentiment="positive", source_label="HN 10↑"),
    }
    filtered = _filter_community_map_by_summary(community_map, community_summary_map)
    assert "https://a.example.com/story" in filtered
    assert "https://missing.example.com/story" not in filtered


def test_filter_handles_empty_summary_map():
    """Defensive: if summarizer failed entirely, pass through unchanged
    (don't break ranking by filtering everything out)."""
    from services.pipeline import _filter_community_map_by_summary

    community_map = {
        "https://a.example.com/story": "blob A",
    }
    filtered = _filter_community_map_by_summary(community_map, {})
    # Empty summary map → pass through (graceful degradation)
    assert filtered == community_map


def test_filter_handles_empty_community_map():
    from services.pipeline import _filter_community_map_by_summary

    community_summary_map = {
        "https://a.example.com/story": CommunityInsight(sentiment="mixed", source_label="HN 1↑"),
    }
    filtered = _filter_community_map_by_summary({}, community_summary_map)
    assert filtered == {}


def test_filter_keeps_when_any_thread_has_sentiment():
    """New shape: if at least one thread has non-null sentiment, keep entry."""
    from services.pipeline import _filter_community_map_by_summary

    community_map = {
        "https://example.com/x": (
            "[Hacker News|url=https://news.ycombinator.com/item?id=1] x | 100 points | 10 comments\n"
            "Top comments:\n"
            "> \"hn quote\"\n\n"
            "[Reddit r/x|url=https://www.reddit.com/r/x/comments/y/z/] x | 50 upvotes | 5 comments\n"
            "Top comments:\n"
            "> \"reddit quote\"\n"
        ),
    }
    community_summary_map = {
        "https://example.com/x": CommunityInsight(threads=[
            ThreadInfo(platform="hackernews", url="https://news.ycombinator.com/item?id=1",
                       upvotes=100, comments=10, sentiment="mixed",
                       quotes=["q"], quotes_ko=["인용"], key_point="kp"),
            ThreadInfo(platform="reddit", url="https://www.reddit.com/r/x/comments/y/z/",
                       subreddit="x", upvotes=50, comments=5, sentiment=None,
                       quotes=[], quotes_ko=[], key_point=None),
        ]),
    }
    filtered = _filter_community_map_by_summary(community_map, community_summary_map)
    assert "https://example.com/x" in filtered


def test_filter_drops_when_all_threads_off_topic():
    """All sentiment=None → drop entry entirely."""
    from services.pipeline import _filter_community_map_by_summary

    community_map = {"https://example.com/x": "blob"}
    community_summary_map = {
        "https://example.com/x": CommunityInsight(threads=[
            ThreadInfo(platform="hackernews", url="https://x", upvotes=100, comments=10,
                       sentiment=None, quotes=[], quotes_ko=[], key_point=None),
            ThreadInfo(platform="reddit", url="https://y", subreddit="x", upvotes=50,
                       comments=5, sentiment=None, quotes=[], quotes_ko=[], key_point=None),
        ]),
    }
    filtered = _filter_community_map_by_summary(community_map, community_summary_map)
    assert "https://example.com/x" not in filtered


def test_filter_redacts_offtopic_platform_section_from_blob():
    """R4: when an entry is kept (one platform relevant, one off-topic), strip
    the off-topic platform's section from the raw blob before passing to
    ranking. Otherwise the off-topic platform's upvote count still inflates
    ranking score."""
    from services.pipeline import _filter_community_map_by_summary

    raw_blob = (
        "[Hacker News|url=https://news.ycombinator.com/item?id=1] HN thread | 100 points | 10 comments\n"
        "Top comments:\n"
        "> \"relevant hn quote\"\n\n"
        "[Reddit r/x|url=https://www.reddit.com/r/x/comments/y/z/] off-topic political | 5000 upvotes | 1000 comments\n"
        "Top comments:\n"
        "> \"Tiananmen tangent\"\n"
        "> \"USA politics rant\"\n"
    )
    community_map = {"https://example.com/x": raw_blob}
    community_summary_map = {
        "https://example.com/x": CommunityInsight(threads=[
            ThreadInfo(platform="hackernews", url="https://news.ycombinator.com/item?id=1",
                       upvotes=100, comments=10, sentiment="mixed",
                       quotes=["relevant hn quote"], quotes_ko=["관련 인용"], key_point="HN"),
            ThreadInfo(platform="reddit", url="https://www.reddit.com/r/x/comments/y/z/",
                       subreddit="x", upvotes=5000, comments=1000, sentiment=None,
                       quotes=[], quotes_ko=[], key_point=None),
        ]),
    }
    filtered = _filter_community_map_by_summary(community_map, community_summary_map)
    assert "https://example.com/x" in filtered
    redacted = filtered["https://example.com/x"]
    # HN section preserved
    assert "Hacker News|url=" in redacted
    assert "100 points" in redacted
    assert "relevant hn quote" in redacted
    # Reddit (off-topic) section REMOVED — its upvote count must not reach ranking
    assert "5000 upvotes" not in redacted
    assert "Reddit r/x" not in redacted
    assert "Tiananmen" not in redacted


def test_filter_passes_blob_unchanged_when_all_threads_relevant():
    """Both threads relevant → keep entry, pass blob unchanged (no redaction
    needed). This is the common case."""
    from services.pipeline import _filter_community_map_by_summary

    raw_blob = (
        "[Hacker News|url=https://news.ycombinator.com/item?id=1] HN | 100 points | 10 comments\n"
        "> \"hn quote\"\n\n"
        "[Reddit r/x|url=https://www.reddit.com/r/x/comments/y/z/] R | 50 upvotes | 5 comments\n"
        "> \"reddit quote\"\n"
    )
    community_map = {"https://example.com/x": raw_blob}
    community_summary_map = {
        "https://example.com/x": CommunityInsight(threads=[
            ThreadInfo(platform="hackernews", url="https://news.ycombinator.com/item?id=1",
                       upvotes=100, comments=10, sentiment="mixed",
                       quotes=["q"], quotes_ko=["인용"], key_point="kp"),
            ThreadInfo(platform="reddit", url="https://www.reddit.com/r/x/comments/y/z/",
                       subreddit="x", upvotes=50, comments=5, sentiment="positive",
                       quotes=["q"], quotes_ko=["인용"], key_point="kp"),
        ]),
    }
    filtered = _filter_community_map_by_summary(community_map, community_summary_map)
    assert filtered["https://example.com/x"] == raw_blob


def test_filter_legacy_insight_works_via_synthesized_threads():
    """Old checkpoints with flat sentiment field hydrate to single thread via
    synthesized_threads(). Filter must use that uniform shape."""
    from services.pipeline import _filter_community_map_by_summary

    community_map = {"https://example.com/x": "blob"}
    community_summary_map = {
        "https://example.com/x": CommunityInsight(
            source_label="Hacker News 100↑ · 10 comments",
            sentiment="mixed",
            quotes=["legacy q"],
            hn_url="https://news.ycombinator.com/item?id=1",
        ),
    }
    filtered = _filter_community_map_by_summary(community_map, community_summary_map)
    assert "https://example.com/x" in filtered


def test_redact_offtopic_handles_blob_with_no_offtopic():
    """If insight has no off-topic threads, redaction is a no-op (return
    blob unchanged)."""
    from services.pipeline import _redact_offtopic_sections

    raw_blob = "[Hacker News|url=https://x/1] x | 100 points | 10 comments\n> \"q\""
    insight = CommunityInsight(threads=[
        ThreadInfo(platform="hackernews", url="https://x/1", upvotes=100, comments=10,
                   sentiment="mixed", quotes=["q"], quotes_ko=["인용"], key_point="kp"),
    ])
    assert _redact_offtopic_sections(raw_blob, insight) == raw_blob


def test_redact_offtopic_returns_empty_string_when_all_offtopic():
    """All threads off-topic → redaction strips everything. Caller should
    check entry-level filter first; this is a defensive guarantee."""
    from services.pipeline import _redact_offtopic_sections

    raw_blob = (
        "[Hacker News|url=https://x/1] x | 100 points | 10 comments\n"
        "> \"off topic\"\n"
    )
    insight = CommunityInsight(threads=[
        ThreadInfo(platform="hackernews", url="https://x/1", upvotes=100, comments=10,
                   sentiment=None, quotes=[], quotes_ko=[], key_point=None),
    ])
    redacted = _redact_offtopic_sections(raw_blob, insight)
    assert "Hacker News" not in redacted
    assert "off topic" not in redacted

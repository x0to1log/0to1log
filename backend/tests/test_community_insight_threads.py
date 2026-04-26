"""Tests for CommunityInsight.threads structure + backward-compat hydration."""

from models.news_pipeline import CommunityInsight, ThreadInfo


def test_thread_info_basic_fields():
    t = ThreadInfo(
        platform="hackernews",
        url="https://news.ycombinator.com/item?id=42",
        upvotes=1041,
        comments=689,
        sentiment="mixed",
        quotes=["a real quote with substance over ten chars"],
        quotes_ko=["충분히 긴 한국어 인용"],
        key_point="Discussion about pricing",
    )
    assert t.platform == "hackernews"
    assert t.upvotes == 1041
    assert t.subreddit is None  # only set for reddit


def test_thread_info_reddit_has_subreddit():
    t = ThreadInfo(
        platform="reddit",
        url="https://www.reddit.com/r/OpenAI/comments/abc/t/",
        subreddit="OpenAI",
        upvotes=642,
        comments=230,
        sentiment="negative",
        quotes=["a real quote"],
        quotes_ko=["인용"],
        key_point="Pricing critique",
    )
    assert t.subreddit == "OpenAI"


def test_community_insight_with_threads():
    insight = CommunityInsight(
        threads=[
            ThreadInfo(
                platform="hackernews",
                url="https://news.ycombinator.com/item?id=42",
                upvotes=1041,
                comments=689,
                sentiment="mixed",
                quotes=["hn quote with substance over ten chars"],
                quotes_ko=["에이치엔 인용 충분히 긴 텍스트"],
                key_point="HN discussion",
            ),
            ThreadInfo(
                platform="reddit",
                url="https://www.reddit.com/r/OpenAI/comments/abc/t/",
                subreddit="OpenAI",
                upvotes=642,
                comments=230,
                sentiment="negative",
                quotes=["reddit quote with substance over ten chars"],
                quotes_ko=["레딧 인용 충분히 긴 텍스트"],
                key_point="Reddit pricing critique",
            ),
        ],
    )
    assert len(insight.threads) == 2
    assert insight.threads[0].platform == "hackernews"
    assert insight.threads[1].platform == "reddit"


def test_community_insight_legacy_hydration_hn_only():
    """Old checkpoint shape (flat fields, no threads) hydrates to a single-thread
    structure so downstream code sees a uniform shape."""
    insight = CommunityInsight(
        source_label="Hacker News 79↑ · 116 comments",
        sentiment="mixed",
        quotes=["legacy hn quote with substance over ten chars"],
        quotes_ko=["레거시 인용 충분히 긴 텍스트"],
        key_point="Legacy discussion",
        hn_url="https://news.ycombinator.com/item?id=42",
    )
    threads = insight.synthesized_threads()
    assert len(threads) == 1
    assert threads[0].platform == "hackernews"
    assert threads[0].url == "https://news.ycombinator.com/item?id=42"
    assert threads[0].upvotes == 79
    assert threads[0].comments == 116
    assert threads[0].sentiment == "mixed"
    assert threads[0].quotes == ["legacy hn quote with substance over ten chars"]


def test_community_insight_legacy_hydration_both_platforms_drops_quotes():
    """Multi-platform legacy insight (HN + Reddit URLs both present) hydrates to
    TWO threads BOTH with empty quotes. Legacy data mixed quotes from both
    platforms with no per-quote tag — we don't know which quote came from
    which platform. Conservative choice: don't invent provenance. Downstream
    falls back to key_point-only rendering for both threads.

    Single-platform legacy (the other test) keeps quotes — provenance is
    unambiguous when only one platform exists."""
    insight = CommunityInsight(
        source_label="Hacker News 1041↑ · 689 comments · r/OpenAI (642↑)",
        sentiment="mixed",
        quotes=["q1 with substance over ten chars", "q2 with substance over ten chars"],
        quotes_ko=["인용 1 충분히 긴", "인용 2 충분히 긴"],
        key_point="Multi-platform discussion",
        hn_url="https://news.ycombinator.com/item?id=47879092",
        reddit_url="https://www.reddit.com/r/OpenAI/comments/1stqlnh/x/",
    )
    threads = insight.synthesized_threads()
    assert len(threads) == 2
    # Find each platform's thread by name (sort order is unspecified for
    # multi-platform legacy — both equally relevant)
    hn = next(t for t in threads if t.platform == "hackernews")
    reddit = next(t for t in threads if t.platform == "reddit")
    assert hn.upvotes == 1041
    assert reddit.upvotes == 642
    # Both threads have EMPTY quotes — legacy provenance is unknown
    assert hn.quotes == []
    assert hn.quotes_ko == []
    assert reddit.quotes == []
    assert reddit.quotes_ko == []
    # Both threads keep the (shared) key_point so downstream can render
    # something via the HasQuotes: no path
    assert hn.key_point == "Multi-platform discussion"
    assert reddit.key_point == "Multi-platform discussion"


def test_community_insight_synthesized_threads_returns_existing_when_present():
    """When threads is already populated (new format), synthesized_threads
    returns it as-is — no re-derivation from flat fields."""
    explicit = ThreadInfo(
        platform="hackernews",
        url="https://news.ycombinator.com/item?id=42",
        upvotes=1041,
        comments=689,
        sentiment="positive",
        quotes=["new format"],
        quotes_ko=["신규 형식"],
        key_point="New format",
    )
    insight = CommunityInsight(threads=[explicit])
    result = insight.synthesized_threads()
    assert len(result) == 1
    assert result[0] is explicit

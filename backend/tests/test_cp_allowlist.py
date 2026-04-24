"""Tests for the writer URL allowlist — it must include thread URLs
(hn_url / reddit_url) from community_summary_map so the writer can emit
[CITE_N] entries pointing at them without schema rejection."""

from models.news_pipeline import ClassifiedGroup, CommunityInsight, GroupedItem


def _make_group(primary_url: str, items_urls: list[str]) -> ClassifiedGroup:
    return ClassifiedGroup(
        group_title="X",
        items=[GroupedItem(url=u, title="x", subcategory="news") for u in items_urls],
        category="research",
        subcategory="news",
        reason="[LEAD] x",
    )


def test_allowlist_includes_hn_url_from_insight():
    from services.pipeline import _build_writer_url_allowlist

    groups = [_make_group("https://example.com/story", ["https://example.com/story"])]
    community_summary_map = {
        "https://example.com/story": CommunityInsight(
            source_label="Hacker News 79↑",
            hn_url="https://news.ycombinator.com/item?id=42",
        ),
    }
    allowlist = _build_writer_url_allowlist(groups, community_summary_map, {})
    assert "https://news.ycombinator.com/item?id=42" in allowlist


def test_allowlist_includes_reddit_url_from_insight():
    from services.pipeline import _build_writer_url_allowlist

    groups = [_make_group("https://example.com/story", ["https://example.com/story"])]
    community_summary_map = {
        "https://example.com/story": CommunityInsight(
            source_label="r/AI (500↑)",
            reddit_url="https://www.reddit.com/r/AI/comments/abc/t/",
        ),
    }
    allowlist = _build_writer_url_allowlist(groups, community_summary_map, {})
    assert "https://www.reddit.com/r/AI/comments/abc/t/" in allowlist


def test_allowlist_includes_both_urls_when_present():
    from services.pipeline import _build_writer_url_allowlist

    groups = [_make_group("https://example.com/story", ["https://example.com/story"])]
    community_summary_map = {
        "https://example.com/story": CommunityInsight(
            source_label="Hacker News 1041↑ · r/OpenAI (642↑)",
            hn_url="https://news.ycombinator.com/item?id=1",
            reddit_url="https://www.reddit.com/r/OpenAI/comments/x/t/",
        ),
    }
    allowlist = _build_writer_url_allowlist(groups, community_summary_map, {})
    assert "https://news.ycombinator.com/item?id=1" in allowlist
    assert "https://www.reddit.com/r/OpenAI/comments/x/t/" in allowlist


def test_allowlist_still_includes_group_items_and_enriched():
    from services.pipeline import _build_writer_url_allowlist

    groups = [_make_group("https://example.com/story", [
        "https://example.com/story",
        "https://example.com/item2",
    ])]
    enriched_map = {
        "https://example.com/story": [
            {"url": "https://example.com/related1"},
            {"url": "https://example.com/related2"},
        ],
    }
    allowlist = _build_writer_url_allowlist(groups, {}, enriched_map)
    assert "https://example.com/story" in allowlist
    assert "https://example.com/item2" in allowlist
    assert "https://example.com/related1" in allowlist
    assert "https://example.com/related2" in allowlist


def test_allowlist_handles_missing_insight_gracefully():
    from services.pipeline import _build_writer_url_allowlist

    groups = [_make_group("https://example.com/story", ["https://example.com/story"])]
    # Insight with no URLs (old checkpoint)
    community_summary_map = {
        "https://example.com/story": CommunityInsight(source_label="Hacker News 5↑"),
    }
    allowlist = _build_writer_url_allowlist(groups, community_summary_map, {})
    assert allowlist == ["https://example.com/story"]

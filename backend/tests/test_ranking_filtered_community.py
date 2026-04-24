"""Tests for the pre-ranking filter that drops community_map entries
whose summarizer marked the thread as irrelevant (sentiment=null).
Without this filter, irrelevant high-upvote threads influence Lead/Supporting
ranking via their upvote counts."""

from models.news_pipeline import CommunityInsight


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

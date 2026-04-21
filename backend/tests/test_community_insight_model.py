"""CommunityInsight model — URL fields are optional and default to None."""

from models.news_pipeline import CommunityInsight


def test_community_insight_defaults_urls_to_none():
    insight = CommunityInsight(source_label="Hacker News 79↑ · 116 comments")
    assert insight.hn_url is None
    assert insight.reddit_url is None


def test_community_insight_accepts_urls():
    insight = CommunityInsight(
        source_label="Hacker News 79↑ · 116 comments",
        hn_url="https://news.ycombinator.com/item?id=12345",
        reddit_url="https://www.reddit.com/r/OpenAI/comments/abc",
    )
    assert insight.hn_url == "https://news.ycombinator.com/item?id=12345"
    assert insight.reddit_url == "https://www.reddit.com/r/OpenAI/comments/abc"


def test_community_insight_hydrates_from_checkpoint_without_urls():
    """Existing checkpoints (pre-this-feature) don't carry url fields.
    Hydration must succeed — missing fields default to None."""
    old_checkpoint_data = {
        "sentiment": "mixed",
        "quotes": ["first quote"],
        "quotes_ko": ["첫 인용"],
        "key_point": "Discussion about X",
        "source_label": "Hacker News 79↑ · 116 comments",
    }
    insight = CommunityInsight(**old_checkpoint_data)
    assert insight.hn_url is None
    assert insight.reddit_url is None
    assert insight.sentiment == "mixed"

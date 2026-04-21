"""news_collection community thread_block — embeds HN/Reddit thread URLs
in the header line so ranking._parse_source_meta can recover them."""

import re


def test_hn_thread_block_embeds_thread_url():
    from services.news_collection import _format_hn_thread_block

    block = _format_hn_thread_block(
        story_id="12345",
        hn_title="Language Model Contains Personality Subnetworks",
        points=58,
        num_comments=34,
        comments_text=['"first comment"', '"second comment"'],
    )
    # Header line includes structured URL token
    assert block.startswith(
        "[Hacker News|url=https://news.ycombinator.com/item?id=12345] "
        "Language Model Contains Personality Subnetworks | 58 points | 34 comments"
    )
    # Comments preserved
    assert "first comment" in block


def test_hn_thread_block_with_no_story_id_omits_url_token():
    """Defensive: if story_id is missing we keep the old header format so
    downstream parsing doesn't break on empty ids."""
    from services.news_collection import _format_hn_thread_block

    block = _format_hn_thread_block(
        story_id="",
        hn_title="Title",
        points=5,
        num_comments=0,
        comments_text=[],
    )
    assert block.startswith("[Hacker News] Title | 5 points | 0 comments")
    assert "url=" not in block.split("\n")[0]


def test_reddit_thread_block_embeds_thread_url():
    from services.news_collection import _format_reddit_thread_block

    block = _format_reddit_thread_block(
        permalink="/r/OpenAI/comments/abc123/new_gpt_release/",
        rd_title="New GPT release",
        subreddit="OpenAI",
        score=500,
        num_comments=120,
        comments_text=['"hot take"'],
    )
    assert block.startswith(
        "[Reddit r/OpenAI|url=https://www.reddit.com/r/OpenAI/comments/abc123/new_gpt_release/] "
        "New GPT release | 500 upvotes | 120 comments"
    )
    assert "hot take" in block


def test_reddit_thread_block_with_no_permalink_omits_url_token():
    from services.news_collection import _format_reddit_thread_block

    block = _format_reddit_thread_block(
        permalink="",
        rd_title="Title",
        subreddit="AI",
        score=10,
        num_comments=0,
        comments_text=[],
    )
    assert block.startswith("[Reddit r/AI] Title | 10 upvotes | 0 comments")
    assert "url=" not in block.split("\n")[0]

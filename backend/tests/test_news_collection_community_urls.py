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

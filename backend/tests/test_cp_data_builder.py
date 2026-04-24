"""Tests for _build_cp_data_entry — builds the per-topic CP Data block
passed to the writer prompt."""

from models.news_pipeline import ClassifiedGroup, CommunityInsight, GroupedItem


def _make_group(primary_url: str = "https://example.com/story", title: str = "Topic A") -> ClassifiedGroup:
    return ClassifiedGroup(
        group_title=title,
        items=[GroupedItem(url=primary_url, title=title, subcategory="news")],
        category="research",
        subcategory="news",
        reason="[LEAD] test",
        primary_url=primary_url,
    )


def test_cp_entry_with_quotes():
    # Import from services.pipeline (not pipeline_digest directly) to avoid
    # circular import issues. The function is re-exported from pipeline.
    from services.pipeline import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="Hacker News 79↑ · 116 comments",
        sentiment="mixed",
        quotes=["first real quote over ten chars"],
        quotes_ko=["열 글자 이상의 실제 인용"],
        key_point="Community is debating the approach",
    )
    entry = _build_cp_data_entry(_make_group(), insight)
    assert entry is not None
    assert "Topic: Topic A" in entry
    assert "Platform: Hacker News 79↑ · 116 comments" in entry
    assert "Sentiment: mixed" in entry
    assert "HasQuotes: yes — emit 1 blockquote(s) below" in entry
    assert 'English quote 1: "first real quote over ten chars"' in entry
    assert 'Korean quote 1 (translation of English quote 1): "열 글자 이상의 실제 인용"' in entry
    assert "Key Discussion: Community is debating the approach" in entry


def test_cp_entry_without_quotes():
    from services.pipeline import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="r/OpenAI (500↑)",
        sentiment="negative",
        quotes=[],
        quotes_ko=[],
        key_point="Users unhappy with pricing",
    )
    entry = _build_cp_data_entry(_make_group(), insight)
    assert entry is not None
    assert "HasQuotes: no — DO NOT emit any blockquote" in entry
    assert "Key Discussion: Users unhappy with pricing" in entry
    assert "English quote" not in entry


def test_cp_entry_returns_none_when_no_content():
    """Insight with no quotes AND no key_point produces nothing useful for CP."""
    from services.pipeline import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="Hacker News 5↑",
        sentiment="neutral",
        quotes=[],
        quotes_ko=[],
        key_point=None,
    )
    assert _build_cp_data_entry(_make_group(), insight) is None


def test_cp_entry_returns_none_when_insight_is_none():
    from services.pipeline import _build_cp_data_entry

    assert _build_cp_data_entry(_make_group(), None) is None


def test_cp_entry_sanitizes_surrounding_quote_marks():
    """Quotes wrapped in extra quote marks (from old checkpoints) are unwrapped."""
    from services.pipeline import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="Hacker News 5↑",
        quotes=['"real quote with wrapping"'],
        quotes_ko=['"실제 인용 감쌈"'],
        key_point="k",
    )
    entry = _build_cp_data_entry(_make_group(), insight)
    assert entry is not None
    assert 'English quote 1: "real quote with wrapping"' in entry
    # Unwrapped (no extra outer quotes)
    assert 'English quote 1: ""real quote with wrapping""' not in entry


def test_cp_entry_rejects_quote_containing_url():
    """Quote with a URL is suspicious (likely summarizer leaked a link) — drop it."""
    from services.pipeline import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="Hacker News 5↑",
        quotes=["Check out https://example.com for details"],
        quotes_ko=["자세한 내용은 https://example.com 참조"],
        key_point="discussion",
    )
    entry = _build_cp_data_entry(_make_group(), insight)
    assert entry is not None
    # URL-containing quote dropped, so HasQuotes becomes no (since clean_quotes is empty)
    assert "HasQuotes: no" in entry

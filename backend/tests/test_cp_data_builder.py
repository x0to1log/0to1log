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
        source_label="Hacker News 79↑ · 25 comments",
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
        source_label="Hacker News 79↑ · 25 comments",
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
        source_label="Hacker News 79↑ · 25 comments",
        quotes=["Check out https://example.com for details"],
        quotes_ko=["자세한 내용은 https://example.com 참조"],
        key_point="discussion",
    )
    entry = _build_cp_data_entry(_make_group(), insight)
    assert entry is not None
    # URL-containing quote dropped, so HasQuotes becomes no (since clean_quotes is empty)
    assert "HasQuotes: no" in entry


def test_cp_entry_sanitizes_curly_quote_marks():
    """Defensive path: LLM summarizer output and old checkpoints may wrap
    quotes in curly/smart quotes (U+201C/U+201D/U+2018/U+2019), not just
    ASCII double/single. The sanitizer must strip those too — the original
    inline code did, and this refactor must preserve that behavior."""
    from services.pipeline import _build_cp_data_entry

    # Use chr() for curly quotes: U+201C and U+201D
    curly_left = chr(0x201C)   # left double quotation mark
    curly_right = chr(0x201D)  # right double quotation mark

    insight = CommunityInsight(
        source_label="Hacker News 79↑ · 25 comments",
        # Outer wrappers are curly double quotes
        quotes=[curly_left + "real quote with curly wrap" + curly_right],
        quotes_ko=[curly_left + "한글 인용을 쓸 때도 안쪽만 남아야 해요" + curly_right],
        key_point="discussion",
    )
    entry = _build_cp_data_entry(_make_group(), insight)
    assert entry is not None
    # Outer curly quotes stripped, only the interior content remains
    # Inside the f-string the sanitizer wraps in ASCII double quotes: "..."
    assert 'English quote 1: "real quote with curly wrap"' in entry
    # The raw curly chars must NOT leak through as outer wrappers
    assert ('English quote 1: ' + curly_left + '"real quote with curly wrap"' + curly_right) not in entry


def test_cp_entry_includes_hn_url_when_present():
    from services.pipeline import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="Hacker News 79↑ · 116 comments",
        quotes=["a real quote over ten chars"],
        quotes_ko=["열 글자 이상 실제 인용"],
        key_point="discussion",
        hn_url="https://news.ycombinator.com/item?id=42",
    )
    entry = _build_cp_data_entry(_make_group(), insight)
    assert entry is not None
    assert "HackerNewsURL: https://news.ycombinator.com/item?id=42" in entry
    # No RedditURL line when reddit_url is None
    assert "RedditURL:" not in entry


def test_cp_entry_includes_reddit_url_when_present():
    from services.pipeline import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="r/OpenAI (500↑)",
        quotes=["a real quote over ten chars"],
        quotes_ko=["열 글자 이상 실제 인용"],
        key_point="discussion",
        reddit_url="https://www.reddit.com/r/OpenAI/comments/abc/t/",
    )
    entry = _build_cp_data_entry(_make_group(), insight)
    assert entry is not None
    assert "RedditURL: https://www.reddit.com/r/OpenAI/comments/abc/t/" in entry
    assert "HackerNewsURL:" not in entry


def test_cp_entry_includes_both_urls_when_present():
    """Multi-platform insight (e.g. GPT-5.5 story had both HN + r/OpenAI)."""
    from services.pipeline import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="Hacker News 1041↑ · 689 comments · r/OpenAI (642↑)",
        quotes=["guardrails quote over ten chars", "pricing quote over ten chars"],
        quotes_ko=["안전장치 인용", "가격 인용"],
        key_point="discussion",
        hn_url="https://news.ycombinator.com/item?id=47879092",
        reddit_url="https://www.reddit.com/r/OpenAI/comments/1stqlnh/x/",
    )
    entry = _build_cp_data_entry(_make_group(), insight)
    assert entry is not None
    assert "HackerNewsURL: https://news.ycombinator.com/item?id=47879092" in entry
    assert "RedditURL: https://www.reddit.com/r/OpenAI/comments/1stqlnh/x/" in entry


def test_cp_entry_without_urls_works_for_old_checkpoints():
    """Insights hydrated from pre-plumbing checkpoints (Apr 21 and before) have
    no hn_url / reddit_url — entry should still build, just without URL lines."""
    from services.pipeline import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="Hacker News 79↑ · 25 comments",
        quotes=["an old-checkpoint quote"],
        quotes_ko=["구 체크포인트 인용"],
        key_point="discussion",
        # hn_url and reddit_url default to None
    )
    entry = _build_cp_data_entry(_make_group(), insight)
    assert entry is not None
    assert "HackerNewsURL:" not in entry
    assert "RedditURL:" not in entry


# -----------------------------------------------------------------------------
# Min community signal threshold (2026-04-25)
# -----------------------------------------------------------------------------

def test_cp_entry_drops_low_signal_thread():
    """Thread with weak community signal (Apr 24 Meta layoff: HN 6↑, 1 comment,
    a single off-the-cuff comment that admits to not reading the article) should
    be excluded — including it as 'community pulse' implies a broader reaction
    that doesn't exist."""
    from services.pipeline import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="Hacker News 6↑ · 1 comments",
        sentiment="negative",
        quotes=["I have no access to the article, so just guessing..."],
        quotes_ko=["기사에 접근할 수 없어 추측만 하는 건데..."],
        key_point="Negative reaction to layoffs",
        hn_url="https://news.ycombinator.com/item?id=47873636",
    )
    assert _build_cp_data_entry(_make_group(), insight) is None


def test_cp_entry_keeps_thread_above_upvote_threshold():
    """50↑ alone (no comment count) is enough signal — drop only when BOTH
    upvote AND comment counts are below threshold."""
    from services.pipeline import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="Hacker News 50↑",  # exactly at upvote boundary
        sentiment="mixed",
        quotes=["a quote with substance and at least ten chars"],
        quotes_ko=["어쩌고 저쩌고 의미있는 인용"],
        key_point="x",
    )
    assert _build_cp_data_entry(_make_group(), insight) is not None


def test_cp_entry_keeps_thread_with_high_comment_count():
    """Active discussion (low upvote but high comment count) is also valid
    signal — keep when comments >= 10."""
    from services.pipeline import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="Hacker News 20↑ · 50 comments",
        sentiment="mixed",
        quotes=["a quote with substance and at least ten chars"],
        quotes_ko=["어쩌고 저쩌고 의미있는 인용"],
        key_point="x",
    )
    assert _build_cp_data_entry(_make_group(), insight) is not None


def test_cp_entry_drops_thread_just_below_both_thresholds():
    """Below upvote threshold AND below comment threshold = drop."""
    from services.pipeline import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="Hacker News 49↑ · 9 comments",
        sentiment="mixed",
        quotes=["a quote with substance and at least ten chars"],
        quotes_ko=["어쩌고 저쩌고 의미있는 인용"],
        key_point="x",
    )
    assert _build_cp_data_entry(_make_group(), insight) is None


def test_cp_entry_handles_K_suffix_in_upvotes():
    """Source label may use 'K' suffix for thousands (e.g. '2.1K↑'). Parse
    correctly so 2.1K = 2100 ≥ 50 → keep."""
    from services.pipeline import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="r/OpenAI (2.1K↑)",
        sentiment="positive",
        quotes=["a quote with substance and at least ten chars"],
        quotes_ko=["어쩌고 저쩌고 의미있는 인용"],
        key_point="x",
    )
    assert _build_cp_data_entry(_make_group(), insight) is not None


def test_cp_entry_drops_empty_source_label():
    """Defensive: missing/empty source_label means we can't gauge signal — drop."""
    from services.pipeline import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="",
        quotes=["a quote with substance and at least ten chars"],
        quotes_ko=["어쩌고 저쩌고 의미있는 인용"],
        key_point="x",
    )
    assert _build_cp_data_entry(_make_group(), insight) is None

"""Tests for summarize_community per-platform restructure: each platform in
the input blob gets its own filter + summarizer call; results aggregated
into CommunityInsight.threads."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from models.news_pipeline import ClassifiedGroup, GroupedItem


def _make_group(primary_url="https://example.com/x", title="Topic A") -> ClassifiedGroup:
    return ClassifiedGroup(
        group_title=title,
        items=[GroupedItem(url=primary_url, title=title, subcategory="news")],
        category="research",
        subcategory="news",
        reason="[LEAD] x",
        primary_url=primary_url,
    )


@pytest.mark.asyncio
async def test_summarize_community_calls_filter_then_summarizer_per_platform():
    """Multi-platform group → filter called twice (once per platform), summarizer
    called twice (once per platform), result has 2 threads in CommunityInsight."""
    from services.agents.ranking import summarize_community

    primary_url = "https://example.com/gpt55"
    blob = (
        "[Hacker News|url=https://news.ycombinator.com/item?id=42] GPT-5.5 | 1041 points | 689 comments\n"
        "Top comments:\n"
        '> "guardrails complaint"\n'
        '> "30 dollar pricing critique"\n\n'
        "[Reddit r/OpenAI|url=https://www.reddit.com/r/OpenAI/comments/abc/t/] GPT-5.5 thread | 642 upvotes | 230 comments\n"
        "Top comments:\n"
        '> "reddit pricing complaint"\n'
        '> "reddit accessibility concern"\n'
    )
    community_map = {primary_url: blob}
    group = _make_group(primary_url, "GPT-5.5 release")

    # Mock filter: passthrough
    async def fake_filter(candidates, article_title, article_excerpt, max_pick=10):
        return candidates[:max_pick], {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110}

    # Mock summarizer LLM: return one quote per call (incrementing)
    call_count = {"n": 0}

    def make_response():
        call_count["n"] += 1
        n = call_count["n"]
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = (
            '{"groups": {"group_0": {"sentiment": "mixed", '
            f'"quotes": ["quote from platform {n}"], '
            f'"quotes_ko": ["인용 플랫폼 {n}"], '
            f'"key_point": "Discussion about platform {n}"'
            '}}}'
        )
        resp.usage = MagicMock(prompt_tokens=200, completion_tokens=50, total_tokens=250)
        return resp

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(side_effect=lambda **kw: make_response())

    with patch("services.agents.ranking.filter_relevant_comments", new=fake_filter), \
         patch("services.agents.ranking.get_openai_client", return_value=fake_client):
        result, usage = await summarize_community(community_map, [group])

    insight = result[primary_url]
    assert len(insight.threads) == 2

    hn = next(t for t in insight.threads if t.platform == "hackernews")
    assert hn.upvotes == 1041
    assert hn.comments == 689
    assert hn.url == "https://news.ycombinator.com/item?id=42"
    assert len(hn.quotes) == 1

    reddit = next(t for t in insight.threads if t.platform == "reddit")
    assert reddit.upvotes == 642
    assert reddit.subreddit == "OpenAI"
    assert reddit.url == "https://www.reddit.com/r/OpenAI/comments/abc/t/"
    assert len(reddit.quotes) == 1


@pytest.mark.asyncio
async def test_summarize_community_single_platform_creates_one_thread():
    """HN-only group → 1 thread in result."""
    from services.agents.ranking import summarize_community

    primary_url = "https://example.com/y"
    blob = (
        "[Hacker News|url=https://news.ycombinator.com/item?id=99] HN thread | 200 points | 50 comments\n"
        "Top comments:\n"
        '> "single quote"\n'
    )
    community_map = {primary_url: blob}
    group = _make_group(primary_url, "Single platform")

    async def fake_filter(candidates, article_title, article_excerpt, max_pick=10):
        return candidates[:max_pick], {}

    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = (
        '{"groups": {"group_0": {"sentiment": "positive", '
        '"quotes": ["q"], "quotes_ko": ["인용"], "key_point": "kp"}}}'
    )
    fake_response.usage = MagicMock(prompt_tokens=100, completion_tokens=20, total_tokens=120)
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch("services.agents.ranking.filter_relevant_comments", new=fake_filter), \
         patch("services.agents.ranking.get_openai_client", return_value=fake_client):
        result, usage = await summarize_community(community_map, [group])

    insight = result[primary_url]
    assert len(insight.threads) == 1
    assert insight.threads[0].platform == "hackernews"


@pytest.mark.asyncio
async def test_summarize_community_skips_irrelevant_per_platform():
    """If summarizer returns sentiment=null for a platform, that thread is
    still recorded (with sentiment=None) so downstream knows the platform was
    processed and judged off-topic — relevance filter is FIRST line of defense;
    this is the SECOND."""
    from services.agents.ranking import summarize_community

    primary_url = "https://example.com/z"
    blob = (
        "[Hacker News|url=https://news.ycombinator.com/item?id=1] DeepSeek | 1700 points | 1357 comments\n"
        "Top comments:\n"
        '> "off-topic political rant"\n'
    )
    community_map = {primary_url: blob}
    group = _make_group(primary_url, "DeepSeek v4")

    async def fake_filter(candidates, article_title, article_excerpt, max_pick=10):
        return candidates[:max_pick], {}

    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = (
        '{"groups": {"group_0": {"sentiment": null, '
        '"quotes": [], "quotes_ko": [], "key_point": null}}}'
    )
    fake_response.usage = MagicMock(prompt_tokens=100, completion_tokens=20, total_tokens=120)
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch("services.agents.ranking.filter_relevant_comments", new=fake_filter), \
         patch("services.agents.ranking.get_openai_client", return_value=fake_client):
        result, usage = await summarize_community(community_map, [group])

    insight = result[primary_url]
    assert len(insight.threads) == 1
    assert insight.threads[0].sentiment is None
    assert insight.threads[0].quotes == []


@pytest.mark.asyncio
async def test_summarize_community_filter_returns_empty_skips_summarizer():
    """If relevance filter returns [] (R3 fail-CLOSED case — Apr 25 DeepSeek),
    the summarizer call is SKIPPED for that platform. ThreadInfo recorded
    with sentiment=None, quotes=[]."""
    from services.agents.ranking import summarize_community

    primary_url = "https://example.com/d"
    blob = (
        "[Hacker News|url=https://news.ycombinator.com/item?id=999] DeepSeek | 1700 points | 1357 comments\n"
        "Top comments:\n"
        '> "Tiananmen tangent"\n'
    )
    community_map = {primary_url: blob}
    group = _make_group(primary_url, "DeepSeek v4")

    summarizer_call_count = {"n": 0}

    async def fake_filter(candidates, article_title, article_excerpt, max_pick=10):
        return [], {}  # fail-CLOSED — relevance filter judged everything off-topic

    def make_summarizer_response(**kw):
        summarizer_call_count["n"] += 1
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = '{"groups": {"group_0": {"sentiment": "mixed", "quotes": [], "quotes_ko": [], "key_point": null}}}'
        resp.usage = MagicMock(prompt_tokens=100, completion_tokens=10, total_tokens=110)
        return resp

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(side_effect=make_summarizer_response)

    with patch("services.agents.ranking.filter_relevant_comments", new=fake_filter), \
         patch("services.agents.ranking.get_openai_client", return_value=fake_client):
        result, usage = await summarize_community(community_map, [group])

    # Summarizer was NOT called (filter returned empty → skip)
    assert summarizer_call_count["n"] == 0

    insight = result[primary_url]
    assert len(insight.threads) == 1
    assert insight.threads[0].sentiment is None
    assert insight.threads[0].quotes == []


@pytest.mark.asyncio
async def test_summarize_community_skips_thread_when_thread_title_mismatches_article():
    """A high-signal community thread should still be dropped when the HN title
    is plainly about a different topic than the selected article.

    This catches cases like a ModelLens paper inheriting an unrelated
    TinyStories HN thread just because generic "language model" comments look
    technically substantive.
    """
    from services.agents.ranking import summarize_community

    primary_url = "https://arxiv.org/abs/2605.07075"
    blob = (
        "[Hacker News|url=https://news.ycombinator.com/item?id=42576755] "
        "TinyStories: How Small Can Language Models Be and Still Speak Coherent English? (2023) "
        "| 218 points | 116 comments\n"
        "Top comments:\n"
        '> "This is done at a reranking step. It is custom and uses date plus relevance."\n'
    )
    group = _make_group(
        primary_url,
        "ModelLens: Finding the Best for Your Task from Myriads of Models",
    )

    filter_calls = {"n": 0}

    async def fake_filter(candidates, article_title, article_excerpt, max_pick=10):
        filter_calls["n"] += 1
        return candidates[:max_pick], {}

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock()

    with patch("services.agents.ranking.filter_relevant_comments", new=fake_filter), \
         patch("services.agents.ranking.get_openai_client", return_value=fake_client):
        result, _usage = await summarize_community({primary_url: blob}, [group])

    insight = result[primary_url]
    assert filter_calls["n"] == 0
    assert len(insight.threads) == 1
    assert insight.threads[0].sentiment is None
    assert insight.threads[0].quotes == []
    fake_client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_summarize_community_keeps_uncertain_generic_thread_title_for_filter():
    """No title overlap is not enough to drop a thread.

    If the article has a named entity but the community title is generic
    rather than a conflicting named topic, let the relevance filter decide.
    """
    from services.agents.ranking import summarize_community

    primary_url = "https://www.reuters.com/business/openai-deployco/"
    blob = (
        "[Hacker News|url=https://news.ycombinator.com/item?id=99] "
        "A new consulting arm for enterprise AI | 120 points | 64 comments\n"
        "Top comments:\n"
        '> "Enterprise integration work is where these systems usually get stuck."\n'
    )
    group = _make_group(
        primary_url,
        "OpenAI creates new unit with $4 billion investment to aid corporate AI push",
    )

    filter_calls = {"n": 0}

    async def fake_filter(candidates, article_title, article_excerpt, max_pick=10):
        filter_calls["n"] += 1
        return candidates[:max_pick], {}

    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = (
        '{"groups": {"group_0": {"sentiment": "mixed", '
        '"quotes": ["Enterprise integration work is where these systems usually get stuck."], '
        '"quotes_ko": ["엔터프라이즈 통합 작업에서 이런 시스템들이 대개 막힙니다."], '
        '"key_point": "Discussion focuses on enterprise integration."}}}'
    )
    fake_response.usage = MagicMock(prompt_tokens=100, completion_tokens=20, total_tokens=120)
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch("services.agents.ranking.filter_relevant_comments", new=fake_filter), \
         patch("services.agents.ranking.get_openai_client", return_value=fake_client):
        result, _usage = await summarize_community({primary_url: blob}, [group])

    insight = result[primary_url]
    assert filter_calls["n"] == 1
    assert fake_client.chat.completions.create.await_count == 1
    assert insight.threads[0].sentiment == "mixed"


@pytest.mark.asyncio
async def test_summarize_community_handles_empty_community_map():
    from services.agents.ranking import summarize_community

    result, usage = await summarize_community({}, [_make_group()])
    assert result == {}

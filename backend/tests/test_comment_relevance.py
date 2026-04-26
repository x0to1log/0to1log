"""Tests for filter_relevant_comments — gpt-5-nano LLM-as-judge picks
article-relevant comments from a candidate pool.

Critical: distinguish API failure (fail-OPEN: top-N voted) from valid
LLM judgment of zero relevant (fail-CLOSED: return []) — the Apr 25
DeepSeek case is the latter and we must let the section drop honestly."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_filter_returns_subset_of_input():
    from services.agents.comment_relevance import filter_relevant_comments

    candidates = [
        "DeepSeek v4 has 1.6T params — interesting MoE arch",
        "USA is descending into totalitarianism, but...",  # off-topic
        "Apache 2.0 license is huge for adoption",
        "Tiananmen Square...",  # off-topic
        "1M context window with cost-efficient inference",
    ]
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = '{"selected_indexes": [0, 2, 4]}'
    fake_response.usage = MagicMock(prompt_tokens=200, completion_tokens=20, total_tokens=220)

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch("services.agents.comment_relevance.get_openai_client", return_value=fake_client):
        result, usage = await filter_relevant_comments(
            candidates,
            article_title="DeepSeek v4 released — open-source 1.6T MoE",
            article_excerpt="Apache 2.0 license, 1M context",
            max_pick=10,
        )

    assert len(result) == 3
    assert "DeepSeek v4" in result[0]
    assert "Apache 2.0" in result[1]
    assert "1M context" in result[2]
    # Off-topic dropped
    assert all("Tiananmen" not in r and "totalitarianism" not in r for r in result)


@pytest.mark.asyncio
async def test_filter_api_failure_fails_open_to_top_n():
    """API failure (network, exception) → fail-OPEN: return candidates[:max_pick].
    Better degraded data than no data when the LLM is unreachable."""
    from services.agents.comment_relevance import filter_relevant_comments

    candidates = [f"comment {i}" for i in range(20)]
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("API down"))

    with patch("services.agents.comment_relevance.get_openai_client", return_value=fake_client):
        result, usage = await filter_relevant_comments(
            candidates,
            article_title="X",
            article_excerpt="Y",
            max_pick=5,
        )

    assert result == candidates[:5]


@pytest.mark.asyncio
async def test_filter_valid_zero_selection_fails_closed_to_empty():
    """Valid LLM response with selected_indexes=[] → fail-CLOSED: return [].
    The LLM correctly judged 'everything is off-topic' (Apr 25 DeepSeek case
    where top-voted comments were political flame wars). Returning anything
    here would re-introduce the noise we just filtered out. Let the
    summarizer's sentiment=null path drop the section honestly."""
    from services.agents.comment_relevance import filter_relevant_comments

    candidates = ["c1", "c2", "c3", "c4", "c5"]
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = '{"selected_indexes": []}'
    fake_response.usage = MagicMock(prompt_tokens=100, completion_tokens=10, total_tokens=110)
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch("services.agents.comment_relevance.get_openai_client", return_value=fake_client):
        result, usage = await filter_relevant_comments(
            candidates,
            article_title="X",
            article_excerpt="Y",
            max_pick=10,
        )

    assert result == []  # fail-closed: empty selection means "drop the section"


@pytest.mark.asyncio
async def test_filter_malformed_response_fails_open():
    """LLM returns malformed JSON shape (not a dict, selected_indexes missing
    or not a list) → fail-OPEN: same as API failure. The LLM didn't make a
    valid judgment, so we treat it as unavailable."""
    from services.agents.comment_relevance import filter_relevant_comments

    candidates = [f"c{i}" for i in range(10)]
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = '{"wrong_field": [1, 2, 3]}'
    fake_response.usage = MagicMock(prompt_tokens=100, completion_tokens=10, total_tokens=110)
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch("services.agents.comment_relevance.get_openai_client", return_value=fake_client):
        result, usage = await filter_relevant_comments(
            candidates,
            article_title="X",
            article_excerpt="Y",
            max_pick=5,
        )

    # fail-open: top-N voted preserved
    assert result == candidates[:5]


@pytest.mark.asyncio
async def test_filter_caps_result_at_max_pick():
    """If LLM returns more than max_pick, truncate to max_pick (preserves
    LLM's ordering — which is presumably most relevant first)."""
    from services.agents.comment_relevance import filter_relevant_comments

    candidates = [f"c{i}" for i in range(20)]
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = '{"selected_indexes": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]}'
    fake_response.usage = MagicMock(prompt_tokens=100, completion_tokens=20, total_tokens=120)
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch("services.agents.comment_relevance.get_openai_client", return_value=fake_client):
        result, usage = await filter_relevant_comments(
            candidates,
            article_title="X",
            article_excerpt="Y",
            max_pick=5,
        )

    assert len(result) == 5
    assert result == ["c0", "c1", "c2", "c3", "c4"]


@pytest.mark.asyncio
async def test_filter_handles_empty_candidates():
    from services.agents.comment_relevance import filter_relevant_comments

    result, usage = await filter_relevant_comments(
        [],
        article_title="X",
        article_excerpt="Y",
        max_pick=10,
    )
    assert result == []
    assert usage == {}


@pytest.mark.asyncio
async def test_filter_handles_invalid_indexes_gracefully():
    """LLM returns out-of-range or non-int indexes; skip them silently. Other
    valid indexes still produce a meaningful subset (NOT a fail-open trigger —
    LLM made a judgment, we just sanitize the output)."""
    from services.agents.comment_relevance import filter_relevant_comments

    candidates = ["c0", "c1", "c2"]
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = '{"selected_indexes": [0, 99, 1, -1, 2, "bad"]}'
    fake_response.usage = MagicMock(prompt_tokens=100, completion_tokens=20, total_tokens=120)
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch("services.agents.comment_relevance.get_openai_client", return_value=fake_client):
        result, usage = await filter_relevant_comments(
            candidates,
            article_title="X",
            article_excerpt="Y",
            max_pick=10,
        )

    # Only valid indexes 0, 1, 2 used; others silently skipped
    assert result == ["c0", "c1", "c2"]


@pytest.mark.asyncio
async def test_filter_all_indexes_invalid_fails_closed():
    """LLM returned indexes but ALL are out of range → resulting list is empty.
    Treat this as fail-CLOSED (the LLM made a judgment, we just couldn't apply
    it; equivalent to selected_indexes=[]). Don't fall back to top-N."""
    from services.agents.comment_relevance import filter_relevant_comments

    candidates = ["c0", "c1", "c2"]
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    # All indexes out of range
    fake_response.choices[0].message.content = '{"selected_indexes": [99, -1, 50]}'
    fake_response.usage = MagicMock(prompt_tokens=100, completion_tokens=20, total_tokens=120)
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch("services.agents.comment_relevance.get_openai_client", return_value=fake_client):
        result, usage = await filter_relevant_comments(
            candidates,
            article_title="X",
            article_excerpt="Y",
            max_pick=10,
        )

    assert result == []

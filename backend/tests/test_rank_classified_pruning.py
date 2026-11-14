import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.news_pipeline import ClassifiedGroup, GroupedItem


def _group(url: str, title: str) -> ClassifiedGroup:
    return ClassifiedGroup(
        group_title=title,
        items=[GroupedItem(url=url, title=title)],
        category="research",
        subcategory="papers",
        reason="selected by classifier",
    )


def _response(payload: dict):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = json.dumps(payload)
    resp.usage = MagicMock(prompt_tokens=100, completion_tokens=20, total_tokens=120)
    return resp


@pytest.mark.asyncio
async def test_rank_classified_drops_omitted_groups_and_orders_supporting():
    """Ranking is the last editorial gate before Writer.

    If the ranker marks weak/filler groups as omit, they should not be passed
    to the digest writer, and supporting groups should follow the ranker's
    importance order rather than the original classifier order.
    """
    from services.agents.ranking import rank_classified

    groups = [
        _group("https://example.com/a", "A strong but not lead paper"),
        _group("https://example.com/b", "B lead paper"),
        _group("https://example.com/c", "C weak filler repo"),
        _group("https://example.com/d", "D useful supporting paper"),
        _group("https://example.com/e", "E stale side item"),
    ]

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=_response({
        "lead": ["https://example.com/b"],
        "supporting": ["https://example.com/d", "https://example.com/a"],
        "omit": [
            {"url": "https://example.com/c", "reason": "weak why-now"},
            {"url": "https://example.com/e", "reason": "stale side item"},
        ],
    }))

    with patch("services.agents.ranking.get_openai_client", return_value=fake_client):
        ranked, _usage = await rank_classified(groups, "research")

    assert [g.primary_url for g in ranked] == [
        "https://example.com/b",
        "https://example.com/d",
        "https://example.com/a",
    ]
    assert ranked[0].reason.startswith("[LEAD]")
    assert ranked[1].reason.startswith("[SUPPORTING]")
    assert ranked[2].reason.startswith("[SUPPORTING]")


@pytest.mark.asyncio
async def test_rank_classified_resolves_item_numbers_in_any_shape():
    """The ranker only sees `[n] title` lines, so it answers with numbers.
    Strings and bracketed forms must resolve too, or its lead/omit choices are
    silently replaced by classifier order."""
    from services.agents.ranking import rank_classified

    groups = [
        _group("https://example.com/a", "A strong but not lead paper"),
        _group("https://example.com/b", "B lead paper"),
        _group("https://example.com/c", "C weak filler repo"),
        _group("https://example.com/d", "D useful supporting paper"),
        _group("https://example.com/e", "E stale side item"),
    ]
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=_response({
        "lead": ["2"],
        "supporting": [4, "[1]"],
        "omit": [{"id": 3, "reason": "weak why-now"}, {"id": "5", "reason": "stale"}],
    }))

    with patch("services.agents.ranking.get_openai_client", return_value=fake_client):
        ranked, _usage = await rank_classified(groups, "research")

    assert [g.primary_url for g in ranked] == [
        "https://example.com/b", "https://example.com/d", "https://example.com/a",
    ]
    prompt = fake_client.chat.completions.create.await_args.kwargs["messages"][0]["content"]
    assert "url1" not in prompt
    assert '"id": 3' in prompt

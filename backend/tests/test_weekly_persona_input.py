"""Weekly persona input and empty-output handling.

2026-W43: _fetch_week_digests never selected content_beginner, so the beginner
weekly got no daily bodies, gpt-6.1-sol returned an empty "en", and the stage
was logged as a 0-char success.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.pipeline import WEEKLY_PERSONAS, _generate_weekly_persona_content
from services.pipeline_persistence import _fetch_week_digests


@pytest.mark.asyncio
async def test_week_digests_select_a_content_column_for_every_weekly_persona():
    supabase = MagicMock()
    query = supabase.table.return_value.select.return_value
    for method in ("eq", "in_", "gte", "lte", "order"):
        getattr(query, method).return_value = query
    query.execute.return_value = SimpleNamespace(data=[])

    await _fetch_week_digests(supabase, "2026-W43", "en")

    columns = {c.strip() for c in supabase.table.return_value.select.call_args.args[0].split(",")}
    for persona in WEEKLY_PERSONAS:
        assert f"content_{persona}" in columns


@pytest.mark.asyncio
async def test_empty_en_body_is_logged_as_a_failed_stage():
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"en": "", "headline": "x"}'))])
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=response)
    errors: list[str] = []

    with patch("services.pipeline._log_stage", new=AsyncMock()) as log_stage, \
         patch("services.pipeline.extract_usage_metrics", return_value={}), \
         patch("services.pipeline.merge_usage_metrics", return_value={}):
        result = await _generate_weekly_persona_content(
            persona="beginner", daily_text="daily bodies", client=client, model="gpt-6.1-sol",
            supabase=MagicMock(), run_id="run", cumulative_usage={}, all_errors=errors,
        )

    assert result is None
    assert errors == ["weekly beginner EN: empty content"]
    stage_args = log_stage.await_args_list[0].args
    assert stage_args[2] == "weekly:beginner:en"
    assert stage_args[3] == "failed"

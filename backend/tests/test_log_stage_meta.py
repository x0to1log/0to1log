import asyncio
from unittest.mock import MagicMock

from services.pipeline import _log_stage


def test_log_stage_includes_cached_tokens_in_debug_meta():
    supabase = MagicMock()
    insert = supabase.table.return_value.insert
    insert.return_value.execute.return_value = MagicMock()

    asyncio.run(_log_stage(
        supabase, "run-1", "test:stage", "ok", 0.0,
        usage={
            "model_used": "gpt-5-mini",
            "input_tokens": 1000,
            "output_tokens": 500,
            "cached_tokens": 800,
            "tokens_used": 1500,
            "cost_usd": 0.001,
        },
    ))

    insert.assert_called_once()
    row = insert.call_args[0][0]
    assert row["debug_meta"]["cached_tokens"] == 800
    assert row["debug_meta"]["input_tokens"] == 1000


def test_log_stage_omits_cached_tokens_when_zero():
    supabase = MagicMock()
    insert = supabase.table.return_value.insert
    insert.return_value.execute.return_value = MagicMock()

    asyncio.run(_log_stage(
        supabase, "run-1", "test:stage", "ok", 0.0,
        usage={"input_tokens": 1000, "output_tokens": 500, "cached_tokens": 0},
    ))

    row = insert.call_args[0][0]
    # When debug_meta key is present, cached_tokens should not be in it (zero filtered)
    # When debug_meta is absent entirely, also acceptable
    assert "cached_tokens" not in row.get("debug_meta", {})

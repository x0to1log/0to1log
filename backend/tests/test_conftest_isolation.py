"""Tests must never reach production services, even when backend/.env exists.

Settings reads `.env` directly (env_file), so deleting os.environ keys alone
let a 2026-10-14 cron test prune production checkpoints.
"""
import pytest

import core.database
from core.config import settings


def test_settings_credentials_are_blank():
    assert settings.supabase_url == ""
    assert settings.supabase_service_key == ""
    assert settings.openai_api_key == ""


def test_get_supabase_returns_none():
    assert core.database.get_supabase() is None


def test_creating_a_supabase_client_fails_loudly():
    with pytest.raises(RuntimeError, match="real Supabase client"):
        core.database.create_client("https://example.supabase.co", "key")

import pytest


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch):
    """Prevent tests from accidentally using real credentials."""
    for key in [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
        "OPENAI_API_KEY",
        "TAVILY_API_KEY",
        "CRON_SECRET",
        "REVALIDATE_SECRET",
        "FASTAPI_URL",
    ]:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def isolate_settings(monkeypatch):
    """Blank credentials that Settings already loaded from backend/.env.

    delenv alone is not enough: Settings reads `.env` itself at import time,
    so tests got a production Supabase client (2026-10-14 checkpoint loss).
    Tests that need a client must patch get_supabase explicitly.
    """
    import core.database
    from core.config import settings

    for field in [
        "supabase_url",
        "supabase_service_key",
        "openai_api_key",
        "tavily_api_key",
        "exa_api_key",
        "brave_api_key",
        "pinecone_api_key",
        "resend_api_key",
        "buttondown_api_key",
        "ga4_credentials_json",
        "cron_secret",
        "revalidate_secret",
        "fastapi_url",
    ]:
        monkeypatch.setattr(settings, field, "")
    monkeypatch.setattr(core.database, "_client", None)

    def _refuse(*_args, **_kwargs):
        raise RuntimeError("Tests must not create a real Supabase client; patch get_supabase")

    monkeypatch.setattr(core.database, "create_client", _refuse)


@pytest.fixture(autouse=True)
def stub_quiz_answer_verification(monkeypatch):
    """Default the daily quiz answer verifier to an "ok" verdict.

    Quiz generation tests script the OpenAI client's responses in order; a real
    verify call would consume them. Tests that exercise verification patch
    `services.pipeline_digest.verify_quiz` themselves, which overrides this.
    """

    async def _ok(client, model, body, quiz, **_):
        return {
            "marked_answer_supported": True,
            "explanation_consistent": True,
            "better_option": None,
            "verdict": "ok",
            "evidence": "stubbed in tests/conftest.py",
        }, {}

    # services.pipeline must load first: pipeline_digest imports from it, and a
    # direct pipeline_digest import on a cold interpreter is circular.
    import services.pipeline  # noqa: F401

    monkeypatch.setattr("services.pipeline_digest.verify_quiz", _ok)

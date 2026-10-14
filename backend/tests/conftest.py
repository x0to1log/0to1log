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

    monkeypatch.setattr("services.pipeline_digest.verify_quiz", _ok)

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

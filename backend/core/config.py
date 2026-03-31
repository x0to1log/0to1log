from datetime import datetime, timedelta, timezone

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str = ""
    supabase_service_key: str = ""
    openai_api_key: str = ""
    openai_model_main: str = "gpt-5"
    openai_model_light: str = "gpt-5-mini"
    openai_model_reasoning: str = "gpt-5-nano"
    pinecone_api_key: str = ""
    pinecone_index_name: str = "news-posts"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    tavily_api_key: str = ""
    exa_api_key: str = ""
    brave_api_key: str = ""
    admin_email: str = "admin@0to1log.com"
    cron_secret: str = ""
    revalidate_secret: str = ""
    fastapi_url: str = ""
    max_auto_terms_per_run: int = 5
    ga4_property_id: str = ""
    ga4_credentials_json: str = ""
    cors_origins: str = '["https://0to1log.com","https://www.0to1log.com"]'
    buttondown_api_key: str = ""
    weekly_email_enabled: bool = False


settings = Settings()

KST = timezone(timedelta(hours=9))


def today_kst() -> str:
    """Return today's date in KST as YYYY-MM-DD string."""
    return datetime.now(KST).strftime("%Y-%m-%d")

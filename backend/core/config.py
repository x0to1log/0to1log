from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str = ""
    supabase_service_key: str = ""
    openai_api_key: str = ""
    openai_model_main: str = "gpt-4o"
    openai_model_light: str = "gpt-4o-mini"
    pinecone_api_key: str = ""
    pinecone_index_name: str = "news-posts"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    tavily_api_key: str = ""
    exa_api_key: str = ""
    admin_email: str = "admin@0to1log.com"
    cron_secret: str = ""
    revalidate_secret: str = ""
    fastapi_url: str = ""
    max_auto_terms_per_run: int = 5


settings = Settings()

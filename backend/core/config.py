from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_service_key: str = ""
    openai_api_key: str = ""
    openai_model_main: str = "gpt-4o"
    openai_model_light: str = "gpt-4o-mini"
    tavily_api_key: str = ""
    admin_email: str = "admin@0to1log.com"
    cron_secret: str = ""
    revalidate_secret: str = ""
    fastapi_url: str = ""

    class Config:
        env_file = ".env"


settings = Settings()

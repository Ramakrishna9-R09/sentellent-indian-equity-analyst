from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Sentellent Indian Equity Analyst"
    environment: str = "development"
    api_prefix: str = "/api"
    web_app_url: str = "http://localhost:3000"

    database_url: str | None = None
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "sentellent"
    database_user: str = "sentellent"
    database_password: str = "change-me-locally"
    dev_bypass_auth: bool = True
    dev_user_email: str = "demo@example.com"
    session_cookie_name: str = "sentellent_session"
    session_cookie_secure: bool = False
    session_ttl_hours: int = 168

    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"

    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    groq_api_key: str | None = None
    groq_chat_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    source_user_agent: str = "SentellentAssessmentBot/1.0"
    news_feed_urls: str = ""
    news_lookback_days: int = 14
    fundamentals_refresh_hours: int = 168
    news_refresh_hours: int = 24
    price_refresh_hours: int = 6
    ingestion_max_attempts: int = 4
    source_archive_bucket: str | None = None
    aws_region: str | None = None

    @field_validator("embedding_dimensions")
    @classmethod
    def validate_embedding_dimensions(cls, value: int) -> int:
        if value != 1536:
            raise ValueError("This migration fixes pgvector dimensions to 1536.")
        return value

    @property
    def parsed_news_feed_urls(self) -> list[str]:
        return [url.strip() for url in self.news_feed_urls.split(",") if url.strip()]

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

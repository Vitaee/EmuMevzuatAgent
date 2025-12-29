"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "mevzuatai_dev"
    database_user: str = "postgres"
    database_password: str = ""

    # Application
    app_name: str = "Mevzuat AI"
    app_debug: bool = False

    # Scraper
    scraper_base_url: str = "https://mevzuat.emu.edu.tr/"
    scraper_concurrency: int = 8
    scraper_timeout_connect: float = 10.0
    scraper_timeout_read: float = 30.0

    # OpenRouter (LLM & Embeddings)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "google/gemini-2.0-flash-exp:free"
    embedding_model: str = "qwen/qwen3-embedding-8b"
    embedding_dim: int = 4096

    @property
    def database_url(self) -> str:
        """Build async PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def database_url_sync(self) -> str:
        """Build sync PostgreSQL connection URL (for Alembic)."""
        return (
            f"postgresql+psycopg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

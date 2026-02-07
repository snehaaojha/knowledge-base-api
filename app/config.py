"""Application configuration from environment variables."""

import logging

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class Settings(BaseSettings):
    """Loads configuration from environment. No secrets in code."""

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.example"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    endee_token: str = ""
    endee_base_url: str | None = None
    app_env: str = "development"
    log_level: str = "INFO"

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        level = (v or "INFO").strip().upper()
        if level not in _VALID_LOG_LEVELS:
            return "INFO"
        return level

    endee_timeout_seconds: int = 30
    index_name: str = "knowledge_base"
    embedding_dimension: int = 384
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 512
    default_top_k: int = 5
    max_top_k: int = 50


settings = Settings()

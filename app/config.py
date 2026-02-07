"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    index_name: str = "knowledge_base"
    embedding_dimension: int = 384
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 512
    chunk_overlap: int = 64
    default_top_k: int = 5
    max_top_k: int = 50


settings = Settings()

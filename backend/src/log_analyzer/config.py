"""Application configuration via environment variables.

Uses Pydantic Settings to load config from env vars / .env file.
All secrets (DB password, AI keys) come from environment — never hardcoded.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        database_url: PostgreSQL connection string (async).
        debug: Enable debug mode (verbose logging, auto-reload).
        openai_api_key: OpenAI API key (optional — AI features disabled if empty).
        deepseek_api_key: DeepSeek API key (optional — AI features disabled if empty).
        upload_dir: Directory for storing uploaded log files.
        max_upload_size_mb: Maximum upload file size in megabytes.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://app:changeme@localhost:5432/log_analyzer"

    # Application
    debug: bool = False
    upload_dir: str = "/app/uploads"
    max_upload_size_mb: int = 500

    # AI (optional)
    openai_api_key: str | None = None
    deepseek_api_key: str | None = None

    @property
    def ai_available(self) -> bool:
        """Check if any AI provider is configured."""
        return bool(self.openai_api_key or self.deepseek_api_key)

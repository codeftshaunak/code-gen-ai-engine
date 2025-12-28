"""Application configuration settings."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application Configuration
    APP_NAME: str = "Builder AI Engine"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    PORT: int = 3100

    # CORS Configuration
    CORS_ORIGINS: str = "*"

    # E2B Sandbox Configuration
    E2B_API_KEY: Optional[str] = None

    # OpenRouter API Configuration (Only provider needed)
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # Default AI Model Configuration
    DEFAULT_AI_MODEL: str = "anthropic/claude-3-5-sonnet-20241022"
    DEFAULT_TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 32000  # Increased to allow detailed, polished, modern UI generation with advanced features

    # Retry Configuration
    MAX_RETRIES: int = 2
    RETRY_DELAY_SECONDS: int = 2

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env file


# Global settings instance
settings = Settings()

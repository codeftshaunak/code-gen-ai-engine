"""
Application Configuration
Centralized settings using Pydantic for validation
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional, Union
import os


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "Builder AI Engine"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    PORT: int = 3100

    # CORS
    CORS_ORIGINS: Union[List[str], str] = "*"

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from string or list"""
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            # Handle comma-separated values
            return [origin.strip() for origin in v.split(",")]
        return v

    # Sandbox Configuration
    SANDBOX_PROVIDER: str = "e2b"  # Options: e2b, vercel
    E2B_API_KEY: Optional[str] = None
    E2B_TIMEOUT_MINUTES: int = 20
    E2B_VITE_PORT: int = 5173
    E2B_WORKING_DIR: str = "/home/user/app"

    VERCEL_TOKEN: Optional[str] = None
    VERCEL_TEAM_ID: Optional[str] = None
    VERCEL_PROJECT_ID: Optional[str] = None
    VERCEL_OIDC_TOKEN: Optional[str] = None
    VERCEL_TIMEOUT_MINUTES: int = 20
    VERCEL_DEV_PORT: int = 3000
    VERCEL_WORKING_DIR: str = "/app"

    # AI Model Configuration
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None

    DEFAULT_AI_MODEL: str = "anthropic/claude-3-5-sonnet-20241022"
    DEFAULT_TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 8000

    # Morph Fast Apply (Optional)
    MORPH_API_KEY: Optional[str] = None

    # Package Installation
    USE_LEGACY_PEER_DEPS: bool = True
    PACKAGE_INSTALL_TIMEOUT: int = 60000
    AUTO_RESTART_VITE: bool = True

    # Code Application
    DEFAULT_REFRESH_DELAY: int = 2000
    PACKAGE_INSTALL_REFRESH_DELAY: int = 5000

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

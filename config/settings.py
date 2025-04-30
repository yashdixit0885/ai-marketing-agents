from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

class Settings(BaseSettings):
    """Application settings."""
    # Google Cloud settings
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_CLOUD_PROJECT: Optional[str] = None
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    GOOGLE_DOCS_REVIEWER_EMAIL: Optional[str] = None

    # Database settings
    DATABASE_URL: str = "postgresql://yashdixit:postgres@localhost/ai_content"

    # Redis settings
    REDIS_URL: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

# Override DATABASE_URL from environment if available
if os.environ.get("DATABASE_URL"):
    settings.DATABASE_URL = os.environ["DATABASE_URL"]
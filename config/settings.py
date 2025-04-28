import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """Application settings."""
    
    # Google Cloud settings
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_CLOUD_PROJECT: Optional[str] = None
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    
    # Database settings
    DATABASE_URL: Optional[str] = "postgresql://localhost/ai_content"
    
    # Redis settings
    REDIS_URL: str = "redis://localhost:6379/0"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    
    # Google Cloud settings
    GOOGLE_API_KEY: str
    GOOGLE_CLOUD_PROJECT: str
    GOOGLE_APPLICATION_CREDENTIALS: str
    
    # Database settings
    DATABASE_URL: str
    
    # Redis settings
    REDIS_URL: str = "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env"

settings = Settings()
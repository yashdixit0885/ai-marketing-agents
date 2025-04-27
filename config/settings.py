from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Project settings
    PROJECT_NAME: str = "AI Content Automation"
    VERSION: str = "0.1.0"
    
    # Google Cloud
    GOOGLE_CLOUD_PROJECT: str
    GOOGLE_APPLICATION_CREDENTIALS: str
    
    # Database
    DATABASE_URL: str
    
    # API Keys
    LINKEDIN_CLIENT_ID: Optional[str] = None
    LINKEDIN_CLIENT_SECRET: Optional[str] = None
    TWITTER_API_KEY: Optional[str] = None
    TWITTER_API_SECRET: Optional[str] = None
    MEDIUM_ACCESS_TOKEN: Optional[str] = None
    SUBSTACK_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
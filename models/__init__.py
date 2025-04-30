from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from config.settings import settings
import os

# Use environment variable if available, otherwise fallback to settings
# Override with direct connection string if issues persist
database_url = os.getenv("DATABASE_URL", "postgresql://yashdixit:postgres@localhost/ai_content")
engine = create_engine(database_url)
db_session = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)

Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    """Initialize the database and create all tables."""
    # Import all models here to avoid circular imports
    # This ensures all models are loaded before table creation
    from .content_models import ResearchItem, Article, SocialPost, Visual, ArticleExport
    from .analytics_models import ContentPerformance
    
    # Import relationships to ensure they are registered
    from .content_models import (
        ResearchItem, Article, SocialPost, Visual, ArticleExport,
        ContentType, ContentTone, VisualType
    )
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    return True
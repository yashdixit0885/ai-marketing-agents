from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from config.settings import settings

engine = create_engine(settings.DATABASE_URL)
db_session = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)

Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    # Import all models
    from .content_models import Article, ResearchItem, SocialPost, Visual
    from .analytics_models import ContentPerformance
    
    # Create tables
    Base.metadata.create_all(bind=engine)
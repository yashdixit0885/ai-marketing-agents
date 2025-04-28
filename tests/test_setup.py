import os
import sys
import logging
from dotenv import load_dotenv

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

import models.content_models as content_models

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def create_tables():
    """Create database tables directly."""
    logger.info("Creating database tables directly")
    
    try:
        from models.base import Base
        from models import engine
        
        # Import all models to ensure they're registered with Base
        from models.content_models import Article, ResearchItem, SocialPost, Visual
        from models.analytics_models import ContentPerformance
        
        # Drop all tables first to avoid conflicts
        Base.metadata.drop_all(engine)
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        logger.info("✅ Tables created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Table creation failed: {str(e)}")
        return False

def test_database_connection():
    """Test database connection."""
    from sqlalchemy import create_engine
    from sqlalchemy.sql import text
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return False
    
    logger.info(f"Testing connection to database: {database_url}")
    
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
            logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return False

def test_gemini_api():
    """Test Gemini API connection."""
    import google.generativeai as genai
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY environment variable not set")
        return False
    
    logger.info("Testing connection to Gemini API")
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content("Hello, Gemini! This is a test.")
        assert response.text
        logger.info(f"✅ Gemini API connection successful: {response.text}")
        return True
    except Exception as e:
        logger.error(f"❌ Gemini API connection failed: {str(e)}")
        return False

def test_redis_connection():
    """Test Redis connection."""
    import redis
    
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        logger.error("REDIS_URL environment variable not set")
        return False
    
    logger.info(f"Testing connection to Redis: {redis_url}")
    
    try:
        r = redis.from_url(redis_url)
        r.ping()
        logger.info("✅ Redis connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {str(e)}")
        return False

def test_models():
    """Test model creation."""
    from models.content_models import Article, ResearchItem
    from models import db_session, init_db
    
    logger.info("Testing model creation")
    
    try:
        # Initialize database (creates tables)
        init_db()
        
        # Create test models
        research = ResearchItem(
            title="Test Research",
            source="Test Source",
            content="Test content for research item"
        )
        
        article = Article(
            title="Test Article",
            content="Test content for article",
            status="draft",
            word_count=5
        )
        
        # Add to session
        db_session.add(research)
        db_session.add(article)
        db_session.commit()
        
        # Verify IDs were created
        assert research.id is not None
        assert article.id is not None
        
        logger.info(f"✅ Model creation successful: Research ID={research.id}, Article ID={article.id}")
        
        # Clean up
        db_session.delete(research)
        db_session.delete(article)
        db_session.commit()
        
        return True
    except Exception as e:
        logger.error(f"❌ Model creation failed: {str(e)}")
        return False

if __name__ == "__main__":
    """Run all tests."""
    all_passed = True
    
    # First test database connection
    if not test_database_connection():
        all_passed = False
        logger.error("Database connection failed, exiting tests")
        sys.exit(1)
    
    # Create tables
    create_tables()
    
    
    tests = [
        test_database_connection,
        test_gemini_api,
        test_redis_connection,
        test_models
    ]
    
    for test in tests:
        if not test():
            all_passed = False
    
    if all_passed:
        logger.info("✅ All tests passed!")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed")
        sys.exit(1)
import pytest
from agents.atomization_agent import AtomizationAgent
from agents.content_agent import ContentAgent
from agents.research_agent import ResearchAgent
from models.content_models import Article, SocialPost
from models import db_session

@pytest.mark.asyncio
async def test_atomization_agent_initialization():
    """Test that the AtomizationAgent initializes correctly."""
    agent = AtomizationAgent()
    assert agent.name == "Atomization Agent"
    assert agent.description == "Extracts content for social media"

@pytest.mark.asyncio
async def test_atomization_agent_run(test_db, mock_gemini_client, monkeypatch):
    """Test that the AtomizationAgent can generate social media content."""
    # Create a test article directly in the database
    article = Article(
        title="Transforming Business Operations with AI",
        content="Test content for article about AI",
        status="draft",
        word_count=100
    )
    test_db.add(article)
    test_db.commit()
    
    # Patch the database access
    def mock_query(cls):
        return test_db.query(cls)
        
    def mock_add(obj):
        test_db.add(obj)
        
    def mock_commit():
        test_db.commit()
    
    monkeypatch.setattr("models.db_session.query", mock_query)
    monkeypatch.setattr("models.db_session.add", mock_add)
    monkeypatch.setattr("models.db_session.commit", mock_commit)
    
    # Mock the platform content generation methods
    async def mock_generate_linkedin_content(self, article):
        return "LinkedIn post content with #hashtags"
    
    async def mock_generate_twitter_content(self, article):
        return "Twitter post content with #hashtags"
    
    monkeypatch.setattr(AtomizationAgent, "_generate_linkedin_content", mock_generate_linkedin_content)
    monkeypatch.setattr(AtomizationAgent, "_generate_twitter_content", mock_generate_twitter_content)
    
    # Arrange
    agent = AtomizationAgent()
    platforms = ["linkedin", "twitter"]
    
    # Act
    social_posts = await agent.run(article.id, platforms)
    
    # Assert
    assert len(social_posts) == 2
    
    linkedin_post = next((post for post in social_posts if post.platform == "linkedin"), None)
    assert linkedin_post is not None
    assert linkedin_post.article_id == article.id
    assert "LinkedIn post content" in linkedin_post.content
    
    twitter_post = next((post for post in social_posts if post.platform == "twitter"), None)
    assert twitter_post is not None
    assert twitter_post.article_id == article.id
    assert "Twitter post content" in twitter_post.content


@pytest.mark.asyncio
async def test_atomization_agent_process(test_db, monkeypatch):
    """Test that the AtomizationAgent can process social post data."""
    # We need to patch the db_session.add and commit methods to avoid conflicts
    def mock_add(obj):
        # Do nothing since we're using test_db directly
        pass
        
    def mock_commit():
        # Do nothing since we'll commit with test_db
        pass
        
    monkeypatch.setattr("models.db_session.add", mock_add)
    monkeypatch.setattr("models.db_session.commit", mock_commit)
    
    # Arrange
    agent = AtomizationAgent()
    
    # Create an article first
    article = Article(
        title="Test Article",
        content="Test content for article",
        status="draft",
        word_count=4
    )
    test_db.add(article)
    test_db.commit()
    
    data = {
        "article": article,
        "content": "This is a test social media post.",
        "platform": "linkedin"
    }
    
    # Act
    social_post = await agent.process(data)
    
    # Add to test_db
    test_db.add(social_post)
    test_db.commit()
    
    # Assert
    assert social_post is not None
    assert isinstance(social_post, SocialPost)
    assert social_post.id is not None
    assert social_post.platform == "linkedin"
    assert social_post.content == data["content"]
    assert social_post.status == "draft"
    assert social_post.article_id == article.id
    
    # Verify it was saved to the database
    db_post = test_db.query(SocialPost).filter_by(id=social_post.id).first()
    assert db_post is not None
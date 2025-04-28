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
async def test_atomization_agent_run(test_db, mock_gemini_client):
    """Test that the AtomizationAgent can generate social media content."""
    # First, create a research item and article
    research_agent = ResearchAgent()
    research_item = await research_agent.run("AI in business")
    
    content_agent = ContentAgent()
    article = await content_agent.run(research_item.id)
    
    # Arrange
    agent = AtomizationAgent()
    platforms = ["linkedin", "twitter"]
    
    # Act
    social_posts = await agent.run(article.id, platforms)
    
    # Assert
    assert social_posts is not None
    assert len(social_posts) == 2
    assert all(isinstance(post, SocialPost) for post in social_posts)
    
    # Check LinkedIn post
    linkedin_post = next((post for post in social_posts if post.platform == "linkedin"), None)
    assert linkedin_post is not None
    assert linkedin_post.article_id == article.id
    assert "AI adoption increased 35%" in linkedin_post.content
    assert "#ArtificialIntelligence" in linkedin_post.content
    assert linkedin_post.status == "draft"
    
    # Check Twitter post
    twitter_post = next((post for post in social_posts if post.platform == "twitter"), None)
    assert twitter_post is not None
    assert twitter_post.article_id == article.id
    assert "62% of businesses report positive ROI" in twitter_post.content
    assert "#AI" in twitter_post.content
    assert twitter_post.status == "draft"
    
    # Verify they were saved to the database
    db_posts = test_db.query(SocialPost).filter(SocialPost.article_id == article.id).all()
    assert len(db_posts) == 2

@pytest.mark.asyncio
async def test_atomization_agent_process(test_db):
    """Test that the AtomizationAgent can process social post data."""
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
    
    # Assert
    assert social_post is not None
    assert isinstance(social_post, SocialPost)
    assert social_post.id is not None
    assert social_post.platform == "linkedin"
    assert social_post.content == data["content"]
    assert social_post.status == "draft"
    assert social_post.article_id == article.id
    
    # Verify it was saved to the database
    db_post = test_db.query(SocialPost).get(social_post.id)
    assert db_post is not None
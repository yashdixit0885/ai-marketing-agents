import pytest
from datetime import datetime, timedelta
from agents.distribution_agent import DistributionAgent
from agents.content_agent import ContentAgent
from agents.research_agent import ResearchAgent
from agents.atomization_agent import AtomizationAgent
from models.content_models import Article, SocialPost
from models import db_session

@pytest.mark.asyncio
async def test_distribution_agent_initialization():
    """Test that the DistributionAgent initializes correctly."""
    agent = DistributionAgent()
    assert agent.name == "Distribution Agent"
    assert agent.description == "Handles content publication and tracking"

@pytest.mark.asyncio
async def test_distribution_agent_run_with_article(test_db, mock_gemini_client):
    """Test that the DistributionAgent can distribute content for an article."""
    # First, create a research item and article
    research_agent = ResearchAgent()
    research_item = await research_agent.run("AI in business")
    
    content_agent = ContentAgent()
    article = await content_agent.run(research_item.id)
    
    # Create social posts for the article
    atomization_agent = AtomizationAgent()
    social_posts = await atomization_agent.run(article.id, ["linkedin", "twitter"])
    
    # Arrange
    agent = DistributionAgent()
    
    # Act
    scheduled_posts = await agent.run(article_id=article.id)
    
    # Assert
    assert scheduled_posts is not None
    assert len(scheduled_posts) == 2
    assert all(isinstance(post, SocialPost) for post in scheduled_posts)
    assert all(post.status == "scheduled" for post in scheduled_posts)
    assert all(post.scheduled_time is not None for post in scheduled_posts)
    
    # Check article status
    article = test_db.query(Article).get(article.id)
    assert article.status == "published"
    
    # Verify posts were updated in the database
    db_posts = test_db.query(SocialPost).filter(SocialPost.article_id == article.id).all()
    assert len(db_posts) == 2
    assert all(post.status == "scheduled" for post in db_posts)

@pytest.mark.asyncio
async def test_distribution_agent_run_with_posts(test_db):
    """Test that the DistributionAgent can distribute specific posts."""
    # Arrange
    agent = DistributionAgent()
    
    # Create an article
    article = Article(
        title="Test Article",
        content="Test content for article",
        status="draft",
        word_count=4
    )
    test_db.add(article)
    
    # Create social posts
    posts = []
    for platform in ["linkedin", "twitter"]:
        post = SocialPost(
            platform=platform,
            content=f"Test content for {platform}",
            status="draft",
            article_id=article.id
        )
        test_db.add(post)
        posts.append(post)
    
    test_db.commit()
    
    # Get post IDs
    post_ids = [post.id for post in posts]
    
    # Act
    scheduled_posts = await agent.run(post_ids=post_ids)
    
    # Assert
    assert scheduled_posts is not None
    assert len(scheduled_posts) == 2
    assert all(isinstance(post, SocialPost) for post in scheduled_posts)
    assert all(post.status == "scheduled" for post in scheduled_posts)
    assert all(post.scheduled_time is not None for post in scheduled_posts)
    
    # Verify posts were updated in the database
    db_posts = test_db.query(SocialPost).filter(SocialPost.id.in_(post_ids)).all()
    assert len(db_posts) == 2
    assert all(post.status == "scheduled" for post in db_posts)

@pytest.mark.asyncio
async def test_distribution_agent_schedule_post(test_db):
    """Test that the DistributionAgent can schedule a post."""
    # Arrange
    agent = DistributionAgent()
    
    # Create an article
    article = Article(
        title="Test Article",
        content="Test content for article",
        status="draft",
        word_count=4
    )
    test_db.add(article)
    test_db.commit()
    
    # Create a social post
    post = SocialPost(
        platform="linkedin",
        content="Test content for LinkedIn",
        status="draft",
        article_id=article.id
    )
    test_db.add(post)
    test_db.commit()
    
    # Act
    scheduled_post = await agent._schedule_post(post)
    
    # Assert
    assert scheduled_post is not None
    assert scheduled_post.status == "scheduled"
    assert scheduled_post.scheduled_time is not None
    
    # The scheduled time should be in the future
    now = datetime.utcnow()
    assert scheduled_post.scheduled_time > now
    
    # Verify the post was updated in the database
    db_post = test_db.query(SocialPost).get(post.id)
    assert db_post.status == "scheduled"
    assert db_post.scheduled_time is not None
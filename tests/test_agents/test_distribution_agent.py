# tests/test_agents/test_distribution_agent.py

import pytest
from datetime import datetime, timedelta
import datetime as dt  # Import the module separately
from unittest.mock import patch
from agents.distribution_agent import DistributionAgent
from models.content_models import Article, SocialPost
from models import db_session

@pytest.mark.asyncio
async def test_distribution_agent_initialization():
    """Test that the DistributionAgent initializes correctly."""
    agent = DistributionAgent()
    assert agent.name == "Distribution Agent"
    assert agent.description == "Handles content publication and tracking"

@pytest.mark.asyncio
async def test_distribution_agent_run_with_article(test_db, monkeypatch):
    """Test that the DistributionAgent can schedule posts for an article."""
    # Create a test article and social posts directly in the database
    article = Article(
        title="Test Article",
        content="Test content for article",
        status="draft",
        word_count=100
    )
    test_db.add(article)
    test_db.commit()
    
    # Create social posts for the article
    platforms = ["linkedin", "twitter"]
    for platform in platforms:
        post = SocialPost(
            platform=platform,
            content=f"Test {platform} post content",
            status="draft",
            article_id=article.id
        )
        test_db.add(post)
    test_db.commit()
    
    # Patch db_session to use our test_db
    def mock_query(cls):
        return test_db.query(cls)
        
    def mock_get(cls, id):
        return test_db.get(cls, id)
        
    def mock_add(obj):
        test_db.add(obj)
        
    def mock_commit():
        test_db.commit()
    
    monkeypatch.setattr("models.db_session.query", mock_query)
    monkeypatch.setattr("models.db_session.get", mock_get)
    monkeypatch.setattr("models.db_session.add", mock_add)
    monkeypatch.setattr("models.db_session.commit", mock_commit)
    
    # Use patch instead of monkeypatch for datetime
    fixed_time = datetime(2025, 1, 1, 12, 0, 0)
    
    # Patch the distribution agent's _schedule_post method instead
    original_schedule_post = DistributionAgent._schedule_post
    
    async def mock_schedule_post(self, post):
        if not post.scheduled_time:
            post.scheduled_time = fixed_time + timedelta(hours=1)
        post.status = "scheduled"
        db_session.commit()
        self.log_status(f"Scheduled post {post.id} for {post.platform} at {post.scheduled_time}")
        return post
    
    monkeypatch.setattr(DistributionAgent, "_schedule_post", mock_schedule_post)
    
    # Arrange
    agent = DistributionAgent()
    
    # Act
    scheduled_posts = await agent.run(article_id=article.id)
    
    # Assert
    assert scheduled_posts is not None
    assert len(scheduled_posts) == 2
    
    for post in scheduled_posts:
        assert post.status == "scheduled"
        assert post.scheduled_time == fixed_time + timedelta(hours=1)
    
    # Verify article status is updated
    article = test_db.query(Article).filter_by(id=article.id).first()
    assert article.status == "published"

@pytest.mark.asyncio
async def test_distribution_agent_process(test_db):
    """Test the process method of DistributionAgent."""
    agent = DistributionAgent()
    data = {"status": "test"}
    
    # Act
    result = await agent.process(data)
    
    # Assert
    assert result["status"] == "Distribution process completed"
    assert result["data"] == data
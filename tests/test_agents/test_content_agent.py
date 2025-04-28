# tests/test_agents/test_content_agent.py
import pytest
from agents.content_agent import ContentAgent
from agents.research_agent import ResearchAgent
from models.content_models import Article, ResearchItem
from models import db_session

@pytest.mark.asyncio
async def test_content_agent_initialization():
    """Test that the ContentAgent initializes correctly."""
    agent = ContentAgent()
    assert agent.name == "Content Agent"
    assert agent.description == "Creates comprehensive articles based on research"

@pytest.mark.asyncio
async def test_content_agent_run(test_db, mock_gemini_client, monkeypatch):
    """Test that the ContentAgent can generate an article from research."""
    # Create a research item directly in the test database
    research_item = ResearchItem(
        title="Test Research",
        source="Test Source",
        content="Test content for research item"
    )
    test_db.add(research_item)
    test_db.commit()
    
    # The content with properly formatted title on the first line
    article_content = "# Transforming Business Operations with AI\n\nIn today's rapidly evolving technological landscape, artificial intelligence (AI) has emerged as a game-changer for businesses across industries..."
    
    # Monkey patch the _generate_article method
    async def mock_generate_article(self, research_item):
        return article_content
    
    # Apply the monkeypatch
    monkeypatch.setattr(ContentAgent, "_generate_article", mock_generate_article)
    
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
    
    # Arrange
    agent = ContentAgent()
    
    # Act
    article = await agent.run(research_item.id)
    
    # Assert
    assert article is not None
    assert article.title == "Transforming Business Operations with AI"
    assert article.status == "draft"
    assert article.word_count > 0
    
    # Verify it was saved to the database
    db_article = test_db.query(Article).filter_by(id=article.id).first()
    assert db_article is not None

@pytest.mark.asyncio
async def test_content_agent_process(test_db, monkeypatch):
    """Test that the ContentAgent can process article data."""
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
    agent = ContentAgent()
    
    # Create a research item first
    research_item = ResearchItem(
        title="Test Research",
        source="Test Source",
        content="Test content for research item"
    )
    test_db.add(research_item)
    test_db.commit()
    
    data = {
        "research_item": research_item,
        "content": "# Test Article\n\nThis is a test article content."
    }
    
    # Act
    article = await agent.process(data)
    
    # Add to test_db
    test_db.add(article)
    test_db.commit()
    
    # Assert
    assert article is not None
    assert isinstance(article, Article)
    assert article.id is not None
    assert article.title == "Test Article"
    assert article.content == data["content"]
    assert article.status == "draft"
    
    # Verify it was saved to the database
    db_article = test_db.query(Article).filter_by(id=article.id).first()
    assert db_article is not None
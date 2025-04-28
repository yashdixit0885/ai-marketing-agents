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
async def test_content_agent_run(test_db, mock_gemini_client):
    """Test that the ContentAgent can generate an article from research."""
    # First, create a research item
    research_agent = ResearchAgent()
    research_item = await research_agent.run("AI in business")
    
    # Arrange
    agent = ContentAgent()
    
    # Act
    article = await agent.run(research_item.id)
    
    # Assert
    assert article is not None
    assert isinstance(article, Article)
    assert article.id is not None
    assert "Transforming Business Operations with AI" in article.title
    assert "AI adoption increased 35%" in article.content
    assert article.status == "draft"
    assert article.word_count > 0
    
    # Verify it was saved to the database
    db_article = test_db.query(Article).get(article.id)
    assert db_article is not None
    assert db_article.content == article.content
    
    # Verify the relationship with research item
    assert research_item in article.research_items

@pytest.mark.asyncio
async def test_content_agent_process(test_db):
    """Test that the ContentAgent can process article data."""
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
    
    # Assert
    assert article is not None
    assert isinstance(article, Article)
    assert article.id is not None
    assert article.title == "Test Article"
    assert article.content == data["content"]
    assert article.status == "draft"
    
    # Verify it was saved to the database
    db_article = test_db.query(Article).get(article.id)
    assert db_article is not None
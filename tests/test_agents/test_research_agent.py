import pytest
from agents.research_agent import ResearchAgent
from models.content_models import ResearchItem
from models import db_session

@pytest.mark.asyncio
async def test_research_agent_initialization():
    """Test that the ResearchAgent initializes correctly."""
    agent = ResearchAgent()
    assert agent.name == "Research Agent"
    assert agent.description == "Conducts deep research on AI business applications"

@pytest.mark.asyncio
async def test_research_agent_run(test_db, mock_gemini_client):
    """Test that the ResearchAgent can run research on a topic."""
    # Arrange
    agent = ResearchAgent()
    topic = "AI in business automation"
    
    # Act
    research_item = await agent.run(topic)
    
    # Assert
    assert research_item is not None
    assert isinstance(research_item, ResearchItem)
    assert research_item.id is not None
    assert research_item.title == "Research on AI topic"
    assert "AI adoption increased 35%" in research_item.content
    assert research_item.meta_data == {"source_type": "ai_generated"}
    
    # Verify it was saved to the database
    db_item = test_db.query(ResearchItem).get(research_item.id)
    assert db_item is not None
    assert db_item.content == research_item.content

@pytest.mark.asyncio
async def test_research_agent_process(test_db, mock_gemini_client):
    """Test that the ResearchAgent can process research data."""
    # Arrange
    agent = ResearchAgent()
    data = """
    # Research Findings on AI Business Applications
    
    ## Key Insights
    - AI adoption increased 35% in enterprise businesses in 2024
    - Natural Language Processing is the most widely adopted AI technology
    """
    
    # Act
    research_item = await agent.process(data)
    
    # Assert
    assert research_item is not None
    assert isinstance(research_item, ResearchItem)
    assert research_item.id is not None
    assert research_item.title == "Research on AI topic"
    assert research_item.content == data
    
    # Verify it was saved to the database
    db_item = test_db.query(ResearchItem).get(research_item.id)
    assert db_item is not None
import pytest
import json
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
async def test_research_agent_run(test_db, mock_gemini_client, monkeypatch):
    """Test that the ResearchAgent can conduct research."""
    # Patch db_session to avoid conflicts
    def mock_add(obj):
        # Directly add to test_db instead
        test_db.add(obj)
        
    def mock_commit():
        # Commit with test_db instead
        test_db.commit()
    
    monkeypatch.setattr("models.db_session.add", mock_add)
    monkeypatch.setattr("models.db_session.commit", mock_commit)
    
    # Arrange
    agent = ResearchAgent()
    topic = "AI business applications"
    
    # Act
    research_item = await agent.run(topic)
    
    # Assert
    assert research_item is not None
    assert isinstance(research_item, ResearchItem)
    assert research_item.id is not None
    assert "Research on AI topic" in research_item.title
    assert research_item.source == "Gemini Research Agent"
    assert research_item.content is not None
    
    # Verify it was saved to the database
    db_research = test_db.query(ResearchItem).filter_by(id=research_item.id).first()
    assert db_research is not None

@pytest.mark.asyncio
async def test_create_research_plan(mock_gemini_client):
    """Test the creation of a research plan."""
    agent = ResearchAgent()
    topic = "AI in business"
    
    # Call the private method
    research_plan = await agent._create_research_plan(topic)
    
    # Verify the structure
    assert isinstance(research_plan, dict)
    assert "key_subtopics" in research_plan
    assert "specific_questions" in research_plan
    assert "important_data_points" in research_plan
    assert "sources_to_prioritize" in research_plan
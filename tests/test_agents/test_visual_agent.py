import os
import pytest
import json
from agents.visual_agent import VisualAgent
from agents.content_agent import ContentAgent
from agents.research_agent import ResearchAgent
from models.content_models import Article, Visual
from models import db_session

@pytest.mark.asyncio
async def test_visual_agent_initialization():
    """Test that the VisualAgent initializes correctly."""
    agent = VisualAgent()
    assert agent.name == "Visual Agent"
    assert agent.description == "Creates visual content to accompany articles"

@pytest.mark.asyncio
async def test_visual_agent_run(test_db, mock_gemini_client, monkeypatch):
    """Test that the VisualAgent can generate visual content."""
    # Create output directory if it doesn't exist
    os.makedirs("data/visuals", exist_ok=True)
    
    # Mock plt.savefig to avoid creating actual files
    def mock_savefig(filename):
        # Just create an empty file
        with open(filename, 'w') as f:
            f.write('')
    
    # Mock plt.close to do nothing
    def mock_close():
        pass
    
    # Apply the monkeypatches
    monkeypatch.setattr("matplotlib.pyplot.savefig", mock_savefig)
    monkeypatch.setattr("matplotlib.pyplot.close", mock_close)
    
    # Mock PIL's Image.save to avoid creating actual files
    def mock_save(self, filename):
        # Just create an empty file
        with open(filename, 'w') as f:
            f.write('')
    
    # Apply the monkeypatch
    monkeypatch.setattr("PIL.Image.Image.save", mock_save)
    
    # First, create a research item and article
    research_agent = ResearchAgent()
    research_item = await research_agent.run("AI in business")
    
    content_agent = ContentAgent()
    article = await content_agent.run(research_item.id)
    
    # Arrange
    agent = VisualAgent()
    
    # Act - Test chart generation
    chart = await agent.run(article.id, "chart")
    
    # Assert
    assert chart is not None
    assert isinstance(chart, Visual)
    assert chart.id is not None
    assert chart.type == "chart"
    assert "chart_" in chart.file_path
    assert os.path.exists(chart.file_path)
    
    # Act - Test quote card generation
    quote_card = await agent.run(article.id, "quote_card")
    
    # Assert
    assert quote_card is not None
    assert isinstance(quote_card, Visual)
    assert quote_card.type == "quote_card"
    assert "quote_" in quote_card.file_path
    assert os.path.exists(quote_card.file_path)
    
    # Verify they were saved to the database
    db_visuals = test_db.query(Visual).filter(Visual.article_id == article.id).all()
    assert len(db_visuals) == 2
    
    # Clean up test files
    for visual in [chart, quote_card]:
        if os.path.exists(visual.file_path):
            os.remove(visual.file_path)

@pytest.mark.asyncio
async def test_visual_agent_process(test_db, monkeypatch):
    """Test that the VisualAgent can process visual data."""
    # Arrange
    agent = VisualAgent()
    
    # Create an article first
    article = Article(
        title="Test Article",
        content="Test content for article",
        status="draft",
        word_count=4
    )
    test_db.add(article)
    test_db.commit()
    
    # Create a test file
    filename = f"data/visuals/test_visual_{article.id}.png"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as f:
        f.write('')
    
    data = {
        "article": article,
        "visual_data": {
            "title": "Test Visual",
            "filename": filename
        },
        "type": "chart"
    }
    
    # Act
    visual = await agent.process(data)
    
    # Assert
    assert visual is not None
    assert isinstance(visual, Visual)
    assert visual.id is not None
    assert visual.type == "chart"
    assert visual.title == "Test Visual"
    assert visual.file_path == filename
    assert visual.article_id == article.id
    
    # Verify it was saved to the database
    db_visual = test_db.query(Visual).get(visual.id)
    assert db_visual is not None
    
    # Clean up test file
    if os.path.exists(filename):
        os.remove(filename)
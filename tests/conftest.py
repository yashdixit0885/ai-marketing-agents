import os
import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.base import Base
from models import db_session, engine

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_engine():
    """Create a SQLAlchemy engine for testing."""
    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()

@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create all tables before a test and drop them after."""
    # Import all models to ensure they're registered with Base
    from models.content_models import Article, ResearchItem, SocialPost, Visual
    from models.analytics_models import ContentPerformance
    
    # Create tables
    Base.metadata.create_all(test_engine)
    
    # Create a new session
    Session = sessionmaker(bind=test_engine)
    session = Session()
    
    # Replace the global session with our test session
    try:
        original_session = db_session.registry()
    except:
        original_session = None
    db_session.remove()
    db_session.configure(bind=test_engine)
    
    yield session
    
    # Clean up
    session.close()
    Base.metadata.drop_all(test_engine)
    
    # Restore original session
    db_session.remove()
    db_session.configure(bind=engine)
    
    # Make sure to clear any lingering state
    db_session.remove()

@pytest.fixture
def mock_gemini_client(monkeypatch):
    """Mock the GeminiClient to avoid actual API calls."""
    class MockGeminiClient:
        async def generate_content(self, prompt):
            """Return a mock response based on the prompt."""
            if "research" in prompt.lower() and "plan" in prompt.lower():
                return """{
                    "key_subtopics": ["AI adoption rates", "ROI metrics", "Implementation challenges", "Industry applications"],
                    "specific_questions": ["What are current AI adoption rates?", "What ROI are businesses seeing?", "What are main implementation barriers?"],
                    "important_data_points": ["35% increase in enterprise AI adoption", "62% report positive ROI", "73% report skill gaps"],
                    "sources_to_prioritize": ["Industry reports", "Case studies", "Academic research"]
                }"""
            elif "collect data" in prompt.lower() or "generate comprehensive research" in prompt.lower():
                return """
                # Research Findings on AI Business Applications
                
                ## Key Insights
                - AI adoption increased 35% in enterprise businesses in 2024
                - Natural Language Processing is the most widely adopted AI technology
                - 62% of businesses report positive ROI from AI implementations
                
                ## Case Studies
                - Company XYZ implemented chatbots and reduced customer service costs by 40%
                - Manufacturing firm ABC used computer vision to reduce defects by 27%
                
                ## Challenges
                - Data quality remains the biggest obstacle to successful AI implementation
                - Skill gaps in workforce reported by 73% of surveyed companies
                """
            elif "article" in prompt.lower():
                return """
                # Transforming Business Operations with AI
                
                In today's rapidly evolving technological landscape, artificial intelligence (AI) has emerged as a game-changer for businesses across industries. Recent studies indicate that AI adoption increased 35% in enterprise businesses in 2024, with Natural Language Processing leading as the most widely adopted AI technology.
                
                ## The Business Case for AI
                
                The appeal of AI lies in its demonstrable return on investment. According to recent surveys, 62% of businesses report positive ROI from AI implementations, with the most successful applications focusing on:
                
                * Customer service automation
                * Predictive maintenance
                * Process optimization
                * Decision support systems
                
                ## Real-World Success Stories
                
                Company XYZ, a mid-sized financial services firm, implemented an AI-powered chatbot system that successfully handled 78% of customer inquiries without human intervention. This resulted in a 40% reduction in customer service costs while improving customer satisfaction ratings by 15%.
                
                ## Implementation Challenges
                
                Despite the promising benefits, businesses face significant hurdles when implementing AI solutions. Data quality remains the biggest obstacle, with inconsistent, incomplete, or biased data compromising the effectiveness of AI systems.
                
                ## Looking Forward
                
                As AI technologies continue to mature, businesses that develop comprehensive data strategies and invest in workforce training will be best positioned to leverage these powerful tools for competitive advantage.
                """
            elif "linkedin" in prompt.lower():
                return """
                🔍 NEW RESEARCH: AI adoption increased 35% among enterprise businesses in 2024, with 62% reporting positive ROI.
                
                Our latest article explores how companies are transforming operations with AI:
                
                • NLP applications lead adoption rates across industries
                • Case study: How Company XYZ reduced customer service costs by 40%
                • Key implementation challenges and solutions
                
                The data is clear - AI isn't just promising theoretical benefits anymore. Real businesses are seeing real results.
                
                What's your biggest challenge with AI implementation?
                
                [Link to full article]
                
                #ArtificialIntelligence #BusinessTransformation #ROI #DigitalStrategy #AIImplementation
                """
            elif "twitter" in prompt.lower():
                return """
                New data: 62% of businesses report positive ROI from AI implementations, yet data quality remains the #1 challenge. See our full analysis: [LINK] #AI #BusinessIntelligence
                """
            elif "chart" in prompt.lower():
                return """
                {
                    "chart_type": "bar",
                    "title": "AI Technology Adoption Rates 2025",
                    "data": [35, 28, 22, 19, 15],
                    "labels": ["NLP", "Predictive Analytics", "Computer Vision", "Process Automation", "Decision Support"],
                    "x_axis": "AI Technology",
                    "y_axis": "Adoption Rate (%)"
                }
                """
            elif "quote" in prompt.lower():
                return """AI adoption increased 35% in enterprise businesses in 2024, with 62% reporting positive ROI on their implementations."""
            elif "infographic" in prompt.lower():
                return """
                {
                    "points": [
                        {"headline": "AI Adoption Rising", "description": "35% increase in enterprise adoption in 2024"},
                        {"headline": "Positive ROI", "description": "62% of companies report positive returns"},
                        {"headline": "Data Quality Matters", "description": "Primary challenge for implementation"}
                    ]
                }
                """
            else:
                return "Generated content for: " + prompt[:50] + "..."
                
    # Patch the GeminiClient in the agents
    from services.api_clients.gemini_client import GeminiClient
    monkeypatch.setattr("services.api_clients.gemini_client.GeminiClient", MockGeminiClient)
    monkeypatch.setattr("agents.research_agent.GeminiClient", MockGeminiClient)
    monkeypatch.setattr("agents.content_agent.GeminiClient", MockGeminiClient)
    monkeypatch.setattr("agents.atomization_agent.GeminiClient", MockGeminiClient)
    monkeypatch.setattr("agents.visual_agent.GeminiClient", MockGeminiClient)
    
    return MockGeminiClient()
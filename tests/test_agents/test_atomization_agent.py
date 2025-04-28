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
    # Monkey patch the ResearchAgent._collect_data method
    async def mock_collect_data(self, topic, research_plan):
        return """
        # Research Findings on AI Business Applications
        
        ## Key Insights
        - AI adoption increased 35% in enterprise businesses in 2024
        - Natural Language Processing is the most widely adopted AI technology
        - 62% of businesses report positive ROI from AI implementations
        """
    
    # Apply the monkeypatch
    monkeypatch.setattr(ResearchAgent, "_collect_data", mock_collect_data)
    
    # Also monkey patch the ContentAgent._generate_article method
    async def mock_generate_article(self, research_item):
        return """
        # Transforming Business Operations with AI
        
        In today's rapidly evolving technological landscape, artificial intelligence (AI) has emerged as a game-changer for businesses across industries...
        """
    
    # Apply the monkeypatch
    monkeypatch.setattr(ContentAgent, "_generate_article", mock_generate_article)
    
    # Monkey patch the _generate_platform_content method to return known content
    async def mock_generate_linkedin_content(self, article):
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
    
    async def mock_generate_twitter_content(self, article):
        return """
        New data: 62% of businesses report positive ROI from AI implementations, yet data quality remains the #1 challenge. See our full analysis: [LINK] #AI #BusinessIntelligence
        """
    
    # Apply the monkeypatches
    monkeypatch.setattr(AtomizationAgent, "_generate_linkedin_content", mock_generate_linkedin_content)
    monkeypatch.setattr(AtomizationAgent, "_generate_twitter_content", mock_generate_twitter_content)
    
    # Patch db_session.query.get to mock database retrieval
    def mock_get(cls, id):
        if cls == Article:
            article = Article(
                id=id,
                title="Transforming Business Operations with AI",
                content="Test content",
                status="draft",
                word_count=100
            )
            return article
        return None
    
    monkeypatch.setattr("models.db_session.query", lambda cls: type('', (), {'get': lambda id: mock_get(cls, id), 'filter': lambda *args: type('', (), {'all': lambda: []})()}))
    
    # Also patch db_session.add and commit
    def mock_add(obj):
        if isinstance(obj, SocialPost):
            obj.id = 1  # Set an ID so we can test it later
        pass
        
    def mock_commit():
        pass
    
    monkeypatch.setattr("models.db_session.add", mock_add)
    monkeypatch.setattr("models.db_session.commit", mock_commit)
    
    # First, create a research item and article
    research_agent = ResearchAgent()
    research_item = await research_agent.run("AI in business")
    
    content_agent = ContentAgent()
    article = await content_agent.run(research_item.id)
    
    # Set IDs for testing
    article.id = 1
    
    # Arrange
    agent = AtomizationAgent()
    platforms = ["linkedin", "twitter"]
    
    # Act
    social_posts = await agent.run(article.id, platforms)
    
    # Add to test_db
    for post in social_posts:
        test_db.add(post)
    test_db.commit()
    
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
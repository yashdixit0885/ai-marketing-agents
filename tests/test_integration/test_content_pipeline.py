import os
import pytest
import json
from datetime import datetime

from agents.research_agent import ResearchAgent
from agents.content_agent import ContentAgent
from agents.visual_agent import VisualAgent
from agents.atomization_agent import AtomizationAgent
from agents.distribution_agent import DistributionAgent

from models.content_models import Article, ResearchItem, SocialPost, Visual
from models import db_session
from utils.agent_metrics import metrics

@pytest.mark.asyncio
async def test_full_content_pipeline(test_db, mock_gemini_client, monkeypatch):
    """Test the entire content pipeline from research to distribution."""
    # Create output directory for visuals
    os.makedirs("data/visuals", exist_ok=True)
    
    # Mock visual creation to avoid file operations
    def mock_savefig(filename):
        # Just create an empty file
        with open(filename, 'w') as f:
            f.write('')
    
    def mock_close():
        pass
    
    def mock_save(self, filename):
        # Just create an empty file
        with open(filename, 'w') as f:
            f.write('')
    
    # Apply the monkeypatches
    monkeypatch.setattr("matplotlib.pyplot.savefig", mock_savefig)
    monkeypatch.setattr("matplotlib.pyplot.close", mock_close)
    monkeypatch.setattr("PIL.Image.Image.save", mock_save)
    
    # Clear any existing metrics
    metrics.clear_metrics()
    
    # Step 1: Research Phase
    print("\n=== Step 1: Research Phase ===")
    research_agent = ResearchAgent()
    research_topic = "AI business applications and ROI in 2025"
    
    print(f"Running research on: {research_topic}")
    run_id = metrics.start_run("Research Agent", "run")
    research_item = await research_agent.run(research_topic)
    metrics.end_run(run_id)
    
    assert research_item is not None
    assert isinstance(research_item, ResearchItem)
    print(f"Research complete: {research_item.id}")
    print(f"Research content sample: {research_item.content[:100]}...")
    
    # Step 2: Content Creation Phase
    print("\n=== Step 2: Content Creation Phase ===")
    content_agent = ContentAgent()
    
    print(f"Generating article from research: {research_item.id}")
    run_id = metrics.start_run("Content Agent", "run")
    article = await content_agent.run(research_item.id)
    metrics.end_run(run_id)
    
    assert article is not None
    assert isinstance(article, Article)
    print(f"Article created: {article.id} - {article.title}")
    print(f"Article content sample: {article.content[:100]}...")
    print(f"Word count: {article.word_count}")
    
    # Step 3: Visual Creation Phase
    print("\n=== Step 3: Visual Creation Phase ===")
    visual_agent = VisualAgent()
    
    print(f"Generating chart for article: {article.id}")
    run_id = metrics.start_run("Visual Agent", "run")
    chart = await visual_agent.run(article.id, "chart")
    metrics.end_run(run_id)
    
    assert chart is not None
    assert isinstance(chart, Visual)
    print(f"Chart created: {chart.id} - {chart.title}")
    print(f"Chart file: {chart.file_path}")
    
    print(f"Generating quote card for article: {article.id}")
    run_id = metrics.start_run("Visual Agent", "run")
    quote_card = await visual_agent.run(article.id, "quote_card")
    metrics.end_run(run_id)
    
    assert quote_card is not None
    assert isinstance(quote_card, Visual)
    print(f"Quote card created: {quote_card.id} - {quote_card.title}")
    print(f"Quote card file: {quote_card.file_path}")
    
    # Step 4: Content Atomization Phase
    print("\n=== Step 4: Content Atomization Phase ===")
    atomization_agent = AtomizationAgent()
    platforms = ["linkedin", "twitter"]
    
    print(f"Generating social media content for article: {article.id}")
    run_id = metrics.start_run("Atomization Agent", "run")
    social_posts = await atomization_agent.run(article.id, platforms)
    metrics.end_run(run_id)
    
    assert social_posts is not None
    assert len(social_posts) == 2
    
    for post in social_posts:
        assert isinstance(post, SocialPost)
        print(f"Social post created for {post.platform}: {post.id}")
        print(f"Content sample: {post.content[:100]}...")
    
    # Step 5: Content Distribution Phase
    print("\n=== Step 5: Content Distribution Phase ===")
    distribution_agent = DistributionAgent()
    
    print(f"Scheduling distribution for article: {article.id}")
    run_id = metrics.start_run("Distribution Agent", "run")
    scheduled_posts = await distribution_agent.run(article_id=article.id)
    metrics.end_run(run_id)
    
    assert scheduled_posts is not None
    assert len(scheduled_posts) == 2
    
    for post in scheduled_posts:
        assert post.status == "scheduled"
        assert post.scheduled_time is not None
        print(f"Post {post.id} scheduled for {post.platform} at {post.scheduled_time}")
    
    # Verify article status has been updated
    article = test_db.query(Article).get(article.id)
    assert article.status == "published"
    print(f"Article status is now: {article.status}")
    
    # Final verification of entire pipeline
    print("\n=== Final Pipeline Verification ===")
    
    # Verify all data in the database
    db_research = test_db.query(ResearchItem).get(research_item.id)
    assert db_research is not None
    
    db_article = test_db.query(Article).get(article.id)
    assert db_article is not None
    assert db_article.status == "published"
    
    db_visuals = test_db.query(Visual).filter(Visual.article_id == article.id).all()
    assert len(db_visuals) == 2
    
    db_posts = test_db.query(SocialPost).filter(SocialPost.article_id == article.id).all()
    assert len(db_posts) == 2
    assert all(post.status == "scheduled" for post in db_posts)
    
    # Performance metrics reporting
    print("\n=== Performance Metrics ===")
    all_metrics = metrics.get_all_metrics()
    
    # Calculate total pipeline duration
    total_duration = sum(m["duration"] for m in all_metrics.values())
    
    print(f"Total pipeline duration: {total_duration:.2f} seconds")
    
    # Report metrics for each agent
    for agent_name in ["Research Agent", "Content Agent", "Visual Agent", "Atomization Agent", "Distribution Agent"]:
        agent_metrics = metrics.get_agent_metrics(agent_name)
        if agent_metrics:
            agent_duration = sum(m["duration"] for m in agent_metrics)
            print(f"{agent_name}: {agent_duration:.2f} seconds ({agent_duration/total_duration*100:.1f}% of total)")
    
    # Export metrics to file for further analysis
    os.makedirs("test_results", exist_ok=True)
    metrics_file = f"test_results/pipeline_metrics_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    metrics.export_metrics(metrics_file)
    print(f"Detailed metrics exported to: {metrics_file}")
    
    print("✅ All pipeline components verified successfully!")
    
    # Clean up test files
    for visual in [chart, quote_card]:
        if os.path.exists(visual.file_path):
            os.remove(visual.file_path)
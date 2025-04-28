from config.celery import celery_app
from agents.content_agent import ContentAgent

@celery_app.task(name="content.generate_article")
async def generate_article(research_item_id):
    """Celery task to generate an article from research."""
    agent = ContentAgent()
    result = await agent.run(research_item_id)
    return result.id
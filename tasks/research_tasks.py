from config.celery import celery_app
from agents.research_agent import ResearchAgent

@celery_app.task(name="research.run_research")
async def run_research(topic):
    """Celery task to run research on a specific topic."""
    agent = ResearchAgent()
    result = await agent.run(topic)
    return result.id
from celery import Celery
from config.settings import settings

celery_app = Celery(
    "ai_content_automation",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["tasks.research_tasks", "tasks.content_tasks"]
)

# Optional configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
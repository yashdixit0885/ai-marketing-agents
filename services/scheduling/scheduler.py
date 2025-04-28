from datetime import datetime, timedelta
from tasks.research_tasks import run_research
from tasks.content_tasks import generate_article
from config.celery import celery_app

class ContentScheduler:
    """Handles scheduling of content creation tasks."""
    
    @staticmethod
    def schedule_weekly_content():
        """Schedule content creation for the week."""
        # Get current date
        now = datetime.utcnow()
        
        # Schedule Article 1 (Tuesday release)
        # Research on Friday
        friday = now + timedelta(days=(4 - now.weekday()) % 7)
        friday_research = run_research.apply_async(
            args=["AI and business automation trends"],
            eta=friday.replace(hour=10, minute=0, second=0)
        )
        
        # Article creation on Monday
        monday = now + timedelta(days=(0 - now.weekday()) % 7 + 7)
        generate_article.apply_async(
            args=[friday_research.id],
            eta=monday.replace(hour=10, minute=0, second=0)
        )
        
        # Schedule Article 2 (Thursday release)
        # Research on Monday
        monday_research = run_research.apply_async(
            args=["AI ethics in business applications"],
            eta=monday.replace(hour=10, minute=0, second=0)
        )
        
        # Article creation on Wednesday
        wednesday = now + timedelta(days=(2 - now.weekday()) % 7 + 7)
        generate_article.apply_async(
            args=[monday_research.id],
            eta=wednesday.replace(hour=10, minute=0, second=0)
        )
        
        return "Weekly content scheduled successfully"
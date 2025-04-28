import logging
from datetime import datetime, timedelta
from .base_agent import BaseAgent
from models.content_models import Article, SocialPost
from models import db_session

logger = logging.getLogger(__name__)

class DistributionAgent(BaseAgent):
    """Agent responsible for distributing content across platforms."""
    
    def __init__(self):
        super().__init__("Distribution Agent", "Handles content publication and tracking")
    
    async def run(self, article_id=None, post_ids=None):
        """Distribute content to platforms."""
        if article_id:
            self.log_status(f"Starting distribution for article: {article_id}")
            
            # Get all social posts for this article
            posts = db_session.query(SocialPost).filter(SocialPost.article_id == article_id).all()
            
            # Schedule each post
            for post in posts:
                await self._schedule_post(post)
            
            # Update article status
            article = db_session.query(Article).get(article_id)
            if article:
                article.status = "published"
                db_session.commit()
                
            self.log_status(f"Completed distribution for article: {article_id}")
            return posts
            
        elif post_ids:
            self.log_status(f"Starting distribution for specific posts")
            
            posts = []
            for post_id in post_ids:
                post = db_session.query(SocialPost).get(post_id)
                if post:
                    await self._schedule_post(post)
                    posts.append(post)
            
            self.log_status(f"Completed distribution for specific posts")
            return posts
            
        else:
            raise ValueError("Either article_id or post_ids must be provided")
    
    async def _schedule_post(self, post):
        """Schedule a post for publication."""
        # Set scheduled time if not already set
        if not post.scheduled_time:
            # Schedule for the future (e.g., 1 hour from now)
            post.scheduled_time = datetime.utcnow() + timedelta(hours=1)
        
        # Update post status
        post.status = "scheduled"
        db_session.commit()
        
        # In a real implementation, this would connect to the actual publishing APIs
        # For now, we'll just log the scheduling
        self.log_status(f"Scheduled post {post.id} for {post.platform} at {post.scheduled_time}")
        
        return post
    
    async def process(self, data):
        """Process distribution analytics."""
        # This would typically handle analytics after distribution
        # For now, it's a placeholder
        return {"status": "Distribution process completed", "data": data}
# agents/export_agent.py

import logging
from datetime import datetime
from .base_agent import BaseAgent
from services.api_clients.google_drive_client import GoogleDriveClient
from services.api_clients.google_docs_client import GoogleDocsClient
from models.content_models import Article, ArticleExport, SocialPost, Visual
from models import db_session
from utils.helpers import slugify

logger = logging.getLogger(__name__)

class ExportAgent(BaseAgent):
    """Agent responsible for exporting content to Google Docs for review."""
    
    def __init__(self):
        super().__init__("Export Agent", "Exports content to Google Docs for review")
        self.drive_client = GoogleDriveClient()
        self.docs_client = GoogleDocsClient()
    
    async def run(self, article_id, reviewer_email=None):
        """Export an article to Google Docs."""
        self.log_status(f"Starting export for article: {article_id}")
        
        # Retrieve the article
        article = db_session.get(Article, article_id)
        if not article:
            raise ValueError(f"Article with ID {article_id} not found")
        
        # Check if we need to create a root folder
        root_folder_id, root_folder_url = await self._get_or_create_root_folder()
        
        # Create a folder for the article
        safe_title = slugify(article.title)
        folder_name = f"Article-{article.id}-{safe_title}"
        folder_id, folder_url = await self.drive_client.create_folder(folder_name, root_folder_id)
        
        # Create main article doc
        doc_name = f"{article.title} - Content"
        doc_id, doc_url = await self.drive_client.create_doc(doc_name, folder_id)
        
        # Write article content to the doc
        await self.docs_client.write_content(doc_id, article.content)
        
        # Create a doc for social posts
        social_posts = db_session.query(SocialPost).filter(SocialPost.article_id == article.id).all()
        if social_posts:
            social_doc_name = f"{article.title} - Social Posts"
            social_doc_id, social_doc_url = await self.drive_client.create_doc(social_doc_name, folder_id)
            
            # Prepare social post content
            social_content = f"# Social Media Posts for '{article.title}'\n\n"
            for post in social_posts:
                social_content += f"## {post.platform.upper()}\n\n"
                social_content += post.content + "\n\n"
                social_content += f"Status: {post.status}\n\n"
                if post.scheduled_time:
                    social_content += f"Scheduled for: {post.scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                social_content += "---\n\n"
            
            # Write social content to the doc
            await self.docs_client.write_content(social_doc_id, social_content)
        
        # Create export record
        export = await self.process({
            "article": article,
            "doc_id": doc_id,
            "doc_url": doc_url,
            "folder_id": folder_id,
            "folder_url": folder_url
        })
        
        # Share with reviewer if email provided
        if reviewer_email:
            await self.drive_client.share_file(folder_id, reviewer_email)
            self.log_status(f"Shared export with reviewer: {reviewer_email}")
        
        # Update article status
        article.status = "review"
        db_session.commit()
        
        self.log_status(f"Completed export for article: {article_id}")
        return export
    
    async def _get_or_create_root_folder(self):
        """Get or create the root folder for all content."""
        # In a real implementation, you might store this ID in a database or settings
        # For simplicity, we'll create a new folder each time
        return await self.drive_client.create_folder("AI Content Automation")
    
    async def process(self, data):
        """Process and store the export record."""
        article = data["article"]
        doc_id = data["doc_id"]
        doc_url = data["doc_url"]
        folder_id = data["folder_id"]
        folder_url = data["folder_url"]
        
        # Create export record
        export = ArticleExport(
            article_id=article.id,
            doc_id=doc_id,
            doc_url=doc_url,
            folder_id=folder_id,
            export_date=datetime.now(),
            status="pending_review"
        )
        
        db_session.add(export)
        db_session.commit()
        
        return export
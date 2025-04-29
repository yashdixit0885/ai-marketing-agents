# agents/export_agent.py

import logging
from datetime import datetime
from .base_agent import BaseAgent
from services.api_clients.google_drive_client import GoogleDriveClient
from services.api_clients.google_docs_client import GoogleDocsClient
from models.content_models import Article, ArticleExport, SocialPost, Visual
from models import db_session
from utils.helpers import slugify
import os

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
        
        # Create or find a folder for the article
        safe_title = slugify(article.title)
        folder_name = f"Article-{article.id}-{safe_title}"
        folder_id, folder_url = await self.drive_client.find_folder_by_name(folder_name, root_folder_id)
        
        if not folder_id:
            # Folder doesn't exist, create it
            folder_id, folder_url = await self.drive_client.create_folder(folder_name, root_folder_id)
            self.log_status(f"Created new folder: {folder_name}")
        else:
            self.log_status(f"Found existing folder: {folder_name}")
        
        # Create or find main article doc
        doc_name = f"{article.title} - Content"
        doc_id, doc_url = await self.drive_client.find_doc_by_name(doc_name, folder_id)
        
        if not doc_id:
            # Document doesn't exist, create it
            doc_id, doc_url = await self.drive_client.create_doc(doc_name, folder_id)
            self.log_status(f"Created new document: {doc_name}")
        else:
            self.log_status(f"Found existing document: {doc_name}")
        
        # Write article content to the doc (replacing existing content)
        await self.docs_client.write_content(doc_id, article.content)
        
        # Create or find a doc for social posts
        social_posts = db_session.query(SocialPost).filter(SocialPost.article_id == article.id).all()
        if social_posts:
            social_doc_name = f"{article.title} - Social Posts"
            social_doc_id, social_doc_url = await self.drive_client.find_doc_by_name(social_doc_name, folder_id)
            
            if not social_doc_id:
                # Document doesn't exist, create it
                social_doc_id, social_doc_url = await self.drive_client.create_doc(social_doc_name, folder_id)
                self.log_status(f"Created new social posts document: {social_doc_name}")
            else:
                self.log_status(f"Found existing social posts document: {social_doc_name}")
            
            
            # Prepare social post content with professional formatting
            social_content = f"# Social Media Posts for '{article.title}'\n\n"
            for post in social_posts:
                social_content += f"## {post.platform.upper()}\n\n"
                
                # Format content differently based on platform
                if post.platform == "linkedin":
                    # LinkedIn posts typically have formatting like bold, bullet points
                    formatted_content = post.content.replace('*', '**')  # Ensure proper bold formatting
                    social_content += formatted_content + "\n\n"
                elif post.platform == "twitter":
                    social_content += post.content + "\n\n"
                
                social_content += f"**Status:** {post.status}\n\n"
                if post.scheduled_time:
                    social_content += f"**Scheduled for:** {post.scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                social_content += "---\n\n"
            
            # Write social content to the doc (replacing existing content)
            await self.docs_client.write_content(social_doc_id, social_content)
        
        # Upload visual files to Google Drive if they exist
        visuals_data = []
        visuals = db_session.query(Visual).filter(Visual.article_id == article.id).all()
        if visuals:
            for visual in visuals:
                if os.path.exists(visual.file_path):
                    # Check if this visual file already exists in the folder
                    visual_name = f"{visual.type}_{visual.title}"
                    existing_files = await self.drive_client.search_files(f"name='{visual_name}'", folder_id)
                    
                    if existing_files:
                        # Use existing file
                        file_id = existing_files[0].get('id')
                        file_url = existing_files[0].get('webViewLink')
                        self.log_status(f"Found existing visual file: {visual_name}")
                    else:
                        # Upload the file to Google Drive
                        file_id, file_url = await self.drive_client.upload_file(
                            visual.file_path, 
                            visual_name, 
                            folder_id
                        )
                        self.log_status(f"Uploaded new visual file: {visual_name}")
                    
                    # Add to visuals data for document creation
                    visuals_data.append({
                        'file_id': file_id,
                        'file_url': file_url,
                        'title': visual.title,
                        'type': visual.type
                    })

        # Create a professional document with integrated visuals
        await self.docs_client.create_professional_document(doc_id, article.content, visuals_data)
        
        # Check if an export record already exists
        existing_export = db_session.query(ArticleExport).filter(
            ArticleExport.article_id == article.id,
            ArticleExport.doc_id == doc_id
        ).first()
        
        if existing_export:
            # Update existing export record
            existing_export.doc_url = doc_url
            existing_export.folder_id = folder_id
            existing_export.export_date = datetime.now()
            existing_export.status = "pending_review"
            db_session.commit()
            export = existing_export
            self.log_status(f"Updated existing export record: {export.id}")
        else:
            # Create new export record
            export = await self.process({
                "article": article,
                "doc_id": doc_id,
                "doc_url": doc_url,
                "folder_id": folder_id,
                "folder_url": folder_url
            })
            self.log_status(f"Created new export record: {export.id}")
        
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
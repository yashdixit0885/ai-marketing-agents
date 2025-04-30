import os
import logging
from typing import Dict, List, Optional, Union
from datetime import datetime
from models.content_models import Article, SocialPost, Visual # Ensure Visual is imported
from services.api_clients.google_docs_client import GoogleDocsClient
from config.settings import settings

logger = logging.getLogger(__name__)

class DocumentExportService:
    """Service for exporting content to Google Docs."""
    
    def __init__(self):
        """Initialize the document export service."""
        self.docs_client = GoogleDocsClient()

    async def export_article_to_docs(self, article_id: int, reviewer_email: Optional[str] = None) -> Dict:
        """Export an article and its associated content to Google Docs, including visuals.
        
        Args:
            article_id: The ID of the article to export
            reviewer_email: Email address of the reviewer to share the document with
            
        Returns:
            Document metadata including the ID and URL
        """
        from models import db_session
        
        # Get the article and associated content
        article = db_session.get(Article, article_id)
        if not article:
            raise ValueError(f"Article with ID {article_id} not found")
        
        # Get visuals (ensure file_path contains the Google Drive ID)
        visuals = db_session.query(Visual).filter_by(article_id=article_id).all()
        logger.info(f"Found {len(visuals)} visuals associated with article {article_id}")
        # Optional: Add a check here to ensure visuals have Drive IDs if needed
        # for v in visuals:
        #     if not v.file_path or v.file_path.startswith('data/'): # Example check
        #         logger.warning(f"Visual {v.id} for article {article_id} might not have a valid Google Drive ID in file_path: {v.file_path}")
        #         # Depending on workflow, might need to trigger upload here or raise error

        # Create Google Doc using the client method that handles content and visuals
        timestamp = datetime.now().strftime("%Y-%m-%d")
        doc_title = f"[REVIEW] {article.title} - {timestamp}"
        
        # Use create_professional_document which handles content and visuals
        # Note: This assumes create_professional_document correctly uses article.content and inserts visuals
        doc_metadata = await self.docs_client.create_professional_document(
            article=article, 
            visuals=visuals
        )
        
        doc_id = doc_metadata.get('documentId')

        if not doc_id:
            logger.error(f"Failed to create or update document for article {article_id}")
            raise RuntimeError("Google Docs export failed: Could not create document.")

        # Add approval form (if still needed - might be handled by create_professional_document or need adjustment)
        # self.docs_client.add_approval_form(doc_id) # Consider if this is still the right place/method

        # Share with reviewer if specified
        if reviewer_email:
            # Assuming sharing is based on the document ID
            shared = self.docs_client.share_document(doc_id, reviewer_email, role='commenter') # Use commenter role for review
            if shared:
                logger.info(f"Document {doc_id} shared with {reviewer_email}")
            else:
                logger.warning(f"Failed to share document {doc_id} with {reviewer_email}")

        # Update article status to indicate it's been sent for review
        article.review_status = "pending"
        article.review_date = None
        article.review_comments = None
        article.reviewed_by = None
        db_session.commit()
        
        logger.info(f"Article {article_id} exported successfully to Google Doc ID: {doc_id}")

        # Return document metadata
        return {
            'document_id': doc_id,
            'title': doc_title, # Use the title we intended
            'url': f"https://docs.google.com/document/d/{doc_id}/edit",
            'review_status': article.review_status
        }

    # Remove or comment out the old _format_article_content method as it's no longer used directly here
    # def _format_article_content(self, article, social_posts, visuals) -> List[Dict]:
    #     ... (old implementation) ...
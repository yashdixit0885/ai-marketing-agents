import logging
from datetime import datetime, timezone
from .base_agent import BaseAgent
from models.content_models import Article
from models import db_session
from services.document_export.export_service import DocumentExportService

logger = logging.getLogger(__name__)

class ReviewAgent(BaseAgent):
    """Agent responsible for content review workflow."""
    
    def __init__(self):
        super().__init__("Review Agent", "Handles content review and approval workflow")
        self.export_service = DocumentExportService()
    
    async def run(self, article_id, reviewer_email=None):
        """Send an article for review.
        
        Args:
            article_id: ID of the article to send for review
            reviewer_email: Email address of the reviewer
            
        Returns:
            Document metadata including ID and URL
        """
        self.log_status(f"Starting review process for article: {article_id}")
        
        # Export to Google Docs
        doc_metadata = await self.export_service.export_article_to_docs(article_id, reviewer_email)
        
        # Update article with Google Docs reference
        article = db_session.get(Article, article_id)
        if article:
            article.google_doc_id = doc_metadata['document_id']
            article.google_doc_url = doc_metadata['url']
            article.status = "review"  # Update status to review
            db_session.commit()
        
        self.log_status(f"Article sent for review: {doc_metadata['url']}")
        
        return doc_metadata
    
    async def process_review_result(self, article_id, review_status, reviewer, comments=None):
        """Process the review results for an article.
        
        Args:
            article_id: ID of the article
            review_status: Status of the review (approved, rejected, needs_revision)
            reviewer: Name or email of the reviewer
            comments: Review comments
            
        Returns:
            Updated article
        """
        self.log_status(f"Processing review result for article: {article_id}")
        
        article = db_session.get(Article, article_id)
        if not article:
            raise ValueError(f"Article with ID {article_id} not found")
        
        # Update review information
        article.review_status = review_status
        article.review_comments = comments
        article.reviewed_by = reviewer
        article.review_date = datetime.now(timezone.utc)
        
        # If approved, update status for distribution
        if review_status == "approved":
            article.status = "published"
            self.log_status(f"Article {article_id} approved for publication")
        elif review_status == "rejected":
            article.status = "draft"
            self.log_status(f"Article {article_id} rejected, marked as draft")
        elif review_status == "needs_revision":
            article.status = "draft"
            self.log_status(f"Article {article_id} needs revision, marked as draft")
        
        db_session.commit()
        
        return article
    
    async def process(self, data):
        """Process review data."""
        # This is a placeholder implementation
        return {"status": "Review process completed", "data": data}
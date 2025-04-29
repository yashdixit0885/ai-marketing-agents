# services/review_handler.py

import logging
from datetime import datetime
from models.content_models import Article, ArticleExport
from models import db_session
from services.api_clients.google_docs_client import GoogleDocsClient

logger = logging.getLogger(__name__)

class ReviewHandler:
    """Handler for processing review results."""
    
    def __init__(self):
        """Initialize the review handler."""
        self.docs_client = GoogleDocsClient()
    
    async def process_review(self, export_id, review_status, review_comments, reviewer_name):
        """Process a review for an article export."""
        try:
            logger.info(f"Processing review for export: {export_id}")
            
            # Get the export
            export = db_session.get(ArticleExport, export_id)
            if not export:
                raise ValueError(f"Export with ID {export_id} not found")
            
            # Get the article
            article = db_session.get(Article, export.article_id)
            if not article:
                raise ValueError(f"Article with ID {export.article_id} not found")
            
            # Update export status
            export.status = review_status
            export.review_comments = review_comments
            export.reviewed_by = reviewer_name
            export.review_date = datetime.now()
            
            # Update article status
            article.review_status = review_status
            article.review_comments = review_comments
            article.reviewed_by = reviewer_name
            article.review_date = datetime.now()
            
            # If approved, mark article as ready for publication
            if review_status == "approved":
                article.status = "published"
                logger.info(f"Article {article.id} approved and ready for publication")
            elif review_status == "rejected":
                article.status = "draft"  # Reset to draft
                logger.info(f"Article {article.id} rejected and reset to draft")
            elif review_status == "needs_revision":
                article.status = "draft"  # Reset to draft for revision
                logger.info(f"Article {article.id} needs revision and reset to draft")
            
            # Save changes
            db_session.commit()
            
            # Add a comment to the Google Doc
            if export.doc_id:
                try:
                    await self.docs_client.add_comment(
                        export.doc_id,
                        f"Review status: {review_status}\nReviewer: {reviewer_name}\nComments: {review_comments}",
                        1,  # Start index (beginning of the document)
                        2   # End index
                    )
                except Exception as e:
                    logger.error(f"Failed to add comment to document: {str(e)}")
            
            return {
                "export_id": export.id,
                "article_id": article.id,
                "status": review_status,
                "reviewer": reviewer_name,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to process review: {str(e)}")
            raise
# tools/review_manager.py

#!/usr/bin/env python3
"""
Review Manager

A command-line tool for managing the review process for AI-generated content.
This tool allows you to export articles to Google Docs, check review status,
and process review decisions.
"""

import os
import sys
import asyncio
import argparse
import logging
from datetime import datetime
from typing import Optional, List

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

# Import project components
from agents.export_agent import ExportAgent
from agents.distribution_agent import DistributionAgent
from models import init_db, db_session
from models.content_models import Article, ArticleExport
from services.review_handler import ReviewHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ReviewManager:
    """Manages the review workflow."""
    
    def __init__(self):
        """Initialize the review manager."""
        self.export_agent = ExportAgent()
        self.distribution_agent = DistributionAgent()
        self.review_handler = ReviewHandler()
    
    async def export_article(self, article_id: int, reviewer_email: Optional[str] = None) -> dict:
        """Export an article to Google Docs for review."""
        logger.info(f"Exporting article {article_id} for review")
        
        # Check if article exists
        article = db_session.get(Article, article_id)
        if not article:
            logger.error(f"Article with ID {article_id} not found")
            return {"status": "error", "message": f"Article with ID {article_id} not found"}
        
        # Export to Google Docs
        export = await self.export_agent.run(article_id, reviewer_email)
        
        return {
            "status": "success",
            "export_id": export.id,
            "doc_url": export.doc_url,
            "message": f"Article exported successfully. Document URL: {export.doc_url}"
        }
    
    async def list_pending_reviews(self) -> List[dict]:
        """List all articles pending review."""
        logger.info("Listing pending reviews")
        
        # Query pending exports
        exports = db_session.query(ArticleExport).filter(
            ArticleExport.status == "pending_review"
        ).all()
        
        results = []
        for export in exports:
            article = db_session.get(Article, export.article_id)
            results.append({
                "export_id": export.id,
                "article_id": export.article_id,
                "title": article.title if article else "Unknown",
                "export_date": export.export_date.strftime("%Y-%m-%d %H:%M:%S") if export.export_date else "Unknown",
                "doc_url": export.doc_url
            })
        
        return results
    
    async def process_review(self, export_id: int, status: str, comments: str, reviewer_name: str) -> dict:
        """Process a review decision."""
        logger.info(f"Processing review for export {export_id}")
        
        if status not in ["approved", "rejected", "needs_revision"]:
            logger.error(f"Invalid status: {status}")
            return {"status": "error", "message": f"Invalid status: {status}. Must be 'approved', 'rejected', or 'needs_revision'"}
        
        result = await self.review_handler.process_review(
            export_id,
            status,
            comments,
            reviewer_name
        )
        
        return {
            "status": "success",
            "review": result,
            "message": f"Review processed successfully. Article status: {status}"
        }
    
    async def distribute_approved(self, article_id: int) -> dict:
        """Distribute an approved article."""
        logger.info(f"Distributing article {article_id}")
        
        # Check article status
        article = db_session.get(Article, article_id)
        if not article:
            logger.error(f"Article with ID {article_id} not found")
            return {"status": "error", "message": f"Article with ID {article_id} not found"}
        
        if article.review_status != "approved":
            logger.warning(f"Article {article_id} not approved (status: {article.review_status})")
            return {"status": "warning", "message": f"Cannot distribute: article has not been approved (status: {article.review_status})"}
        
        # Distribute
        posts = await self.distribution_agent.run(article_id=article_id)
        
        return {
            "status": "success",
            "posts_scheduled": len(posts),
            "message": f"Article distributed successfully. {len(posts)} posts scheduled."
        }
    
    async def list_approved_articles(self) -> List[dict]:
        """List all approved articles."""
        logger.info("Listing approved articles")
        
        articles = db_session.query(Article).filter(
            Article.review_status == "approved"
        ).all()
        
        results = []
        for article in articles:
            results.append({
                "article_id": article.id,
                "title": article.title,
                "status": article.status,
                "review_date": article.review_date.strftime("%Y-%m-%d %H:%M:%S") if article.review_date else "Unknown",
                "reviewed_by": article.reviewed_by
            })
        
        return results

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Manage the review workflow for AI-generated content")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export an article to Google Docs for review")
    export_parser.add_argument("article_id", type=int, help="ID of the article to export")
    export_parser.add_argument("--email", type=str, help="Email of the reviewer to share with")
    
    # List pending reviews command
    list_parser = subparsers.add_parser("list-pending", help="List all articles pending review")
    
    # Process review command
    review_parser = subparsers.add_parser("review", help="Process a review decision")
    review_parser.add_argument("export_id", type=int, help="ID of the export to review")
    review_parser.add_argument("status", choices=["approved", "rejected", "needs_revision"], help="Review decision")
    review_parser.add_argument("--comments", type=str, default="", help="Review comments")
    review_parser.add_argument("--reviewer", type=str, required=True, help="Name of the reviewer")
    
    # Distribute command
    distribute_parser = subparsers.add_parser("distribute", help="Distribute an approved article")
    distribute_parser.add_argument("article_id", type=int, help="ID of the article to distribute")
    
    # List approved articles command
    approved_parser = subparsers.add_parser("list-approved", help="List all approved articles")
    
    return parser.parse_args()

async def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Initialize database
    init_db()
    
    manager = ReviewManager()
    
    if args.command == "export":
        result = await manager.export_article(args.article_id, args.email)
        print(f"Result: {result['status']}")
        print(f"Message: {result['message']}")
        if "doc_url" in result:
            print(f"Document URL: {result['doc_url']}")
    
    elif args.command == "list-pending":
        pending = await manager.list_pending_reviews()
        print(f"Found {len(pending)} pending reviews:")
        for idx, item in enumerate(pending, 1):
            print(f"{idx}. Export ID: {item['export_id']}, Article: {item['article_id']} - {item['title']}")
            print(f"   Exported on: {item['export_date']}")
            print(f"   Doc URL: {item['doc_url']}")
            print()
    
    elif args.command == "review":
        result = await manager.process_review(args.export_id, args.status, args.comments, args.reviewer)
        print(f"Result: {result['status']}")
        print(f"Message: {result['message']}")
    
    elif args.command == "distribute":
        result = await manager.distribute_approved(args.article_id)
        print(f"Result: {result['status']}")
        print(f"Message: {result['message']}")
    
    elif args.command == "list-approved":
        approved = await manager.list_approved_articles()
        print(f"Found {len(approved)} approved articles:")
        for idx, item in enumerate(approved, 1):
            print(f"{idx}. Article ID: {item['article_id']} - {item['title']}")
            print(f"   Status: {item['status']}")
            print(f"   Reviewed by: {item['reviewed_by']} on {item['review_date']}")
            print()
    
    else:
        print("No command specified. Use --help for usage information.")

if __name__ == "__main__":
    asyncio.run(main())
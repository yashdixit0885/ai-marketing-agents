# tools/pipeline_runner.py (updating the existing file)

#!/usr/bin/env python3
"""
Pipeline Runner

A command-line tool to run the entire content generation pipeline manually.
This is useful for testing and demonstration purposes.
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
from agents.research_agent import ResearchAgent
from agents.content_agent import ContentAgent
from agents.visual_agent import VisualAgent
from agents.atomization_agent import AtomizationAgent
from agents.distribution_agent import DistributionAgent
from agents.export_agent import ExportAgent  # New import
from models import init_db, db_session
from models.content_models import Article, ResearchItem, SocialPost, Visual
from services.review_handler import ReviewHandler  # New import

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PipelineRunner:
    """Runs the content generation pipeline."""
    
    def __init__(self):
        """Initialize the pipeline runner."""
        self.research_agent = ResearchAgent()
        self.content_agent = ContentAgent()
        self.visual_agent = VisualAgent()
        self.atomization_agent = AtomizationAgent()
        self.export_agent = ExportAgent()  # New agent
        self.distribution_agent = DistributionAgent()
        self.review_handler = ReviewHandler()  # New handler
    
    async def run_full_pipeline(self, topic: str, platforms: List[str] = None, visual_types: List[str] = None, reviewer_email: Optional[str] = None) -> dict:
        """Run the entire content generation pipeline."""
        if platforms is None:
            platforms = ["linkedin", "twitter"]
        
        if visual_types is None:
            visual_types = ["chart", "quote_card"]
        
        start_time = datetime.now()
        logger.info(f"Starting full pipeline for topic: {topic}")
        
        # Step 1: Research
        logger.info("=== STEP 1: RESEARCH ===")
        research_item = await self.research_agent.run(topic)
        logger.info(f"Research complete: {research_item.id}")
        
        # Step 2: Content creation
        logger.info("=== STEP 2: CONTENT CREATION ===")
        article = await self.content_agent.run(research_item.id)
        logger.info(f"Article created: {article.id} - {article.title}")
        
        # Step 3: Visual creation
        logger.info("=== STEP 3: VISUAL CREATION ===")
        visuals = []
        for visual_type in visual_types:
            logger.info(f"Generating {visual_type} for article: {article.id}")
            visual = await self.visual_agent.run(article.id, visual_type)
            visuals.append(visual)
            logger.info(f"Visual created: {visual.id} - {visual.title}")
        
        # Step 4: Content atomization
        logger.info("=== STEP 4: CONTENT ATOMIZATION ===")
        logger.info(f"Generating social media content for article: {article.id}")
        social_posts = await self.atomization_agent.run(article.id, platforms)
        
        for post in social_posts:
            logger.info(f"Social post created for {post.platform}: {post.id}")
        
        # Step 5: Export for review
        logger.info("=== STEP 5: EXPORT FOR REVIEW ===")
        logger.info(f"Exporting article for review: {article.id}")
        export = await self.export_agent.run(article.id, reviewer_email)
        logger.info(f"Article exported: {export.id} - {export.doc_url}")
        
        # Calculate elapsed time
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info(f"Pipeline completed up to review in {duration}")
        logger.info(f"The article is now ready for review. Please review it at: {export.doc_url}")
        
        # Return the results
        return {
            "research_item": research_item,
            "article": article,
            "visuals": visuals,
            "social_posts": social_posts,
            "export": export,
            "elapsed_time": duration
        }
    
    async def run_partial_pipeline(self, start_point: str, item_id: int, platforms: List[str] = None, visual_types: List[str] = None, reviewer_email: Optional[str] = None) -> dict:
        """Run a portion of the pipeline starting from a specific point."""
        if platforms is None:
            platforms = ["linkedin", "twitter"]
        
        if visual_types is None:
            visual_types = ["chart", "quote_card"]
        
        results = {}
        
        if start_point == "content":
            # Start from content creation
            logger.info(f"Starting pipeline from content creation for research item: {item_id}")
            article = await self.content_agent.run(item_id)
            results["article"] = article
            
            # Continue with visuals, atomization, and export
            # ... (similar to full pipeline)
        
        elif start_point == "visual":
            # Start from visual creation
            logger.info(f"Starting pipeline from visual creation for article: {item_id}")
            article = db_session.get(Article, item_id)
            if not article:
                raise ValueError(f"Article with ID {item_id} not found")
            
            results["article"] = article
            
            # Continue with visuals, atomization, and export
            # ... (similar to full pipeline)
        
        elif start_point == "atomization":
            # Start from atomization
            logger.info(f"Starting pipeline from atomization for article: {item_id}")
            article = db_session.get(Article, item_id)
            if not article:
                raise ValueError(f"Article with ID {item_id} not found")
            
            results["article"] = article
            
            # Continue with atomization and export
            # ... (similar to full pipeline)
        
        elif start_point == "export":
            # Start from export
            logger.info(f"Starting pipeline from export for article: {item_id}")
            article = db_session.get(Article, item_id)
            if not article:
                raise ValueError(f"Article with ID {item_id} not found")
            
            results["article"] = article
            export = await self.export_agent.run(article.id, reviewer_email)
            results["export"] = export
        
        elif start_point == "distribution":
            # Start from distribution
            logger.info(f"Starting pipeline from distribution for article: {item_id}")
            
            # Check if article is approved
            article = db_session.get(Article, item_id)
            if not article:
                raise ValueError(f"Article with ID {item_id} not found")
            
            if article.review_status != "approved":
                logger.warning(f"Article {item_id} is not approved (status: {article.review_status})")
                results["warning"] = f"Article is not approved (status: {article.review_status})"
            else:
                results["scheduled_posts"] = await self.distribution_agent.run(article_id=item_id)
        
        else:
            raise ValueError(f"Unknown start point: {start_point}")
        
        return results
    
    async def process_review(self, export_id: int, status: str, comments: str, reviewer_name: str) -> dict:
        """Process a review."""
        logger.info(f"Processing review for export: {export_id}")
        
        result = await self.review_handler.process_review(
            export_id,
            status,
            comments,
            reviewer_name
        )
        
        logger.info(f"Review processed: {result}")
        return result
    
    def display_results(self, results: dict) -> None:
        """Display the results of the pipeline run."""
        article = results.get("article")
        if article:
            print("\n=== ARTICLE ===")
            print(f"Title: {article.title}")
            print(f"Word count: {article.word_count}")
            print(f"Status: {article.status}")
            print(f"Review status: {article.review_status}")
            print("\nContent preview:")
            print(article.content[:500] + "...")
        
        visuals = results.get("visuals", [])
        if visuals:
            print("\n=== VISUALS ===")
            for visual in visuals:
                print(f"{visual.type}: {visual.title}")
                print(f"File: {visual.file_path}")
        
        social_posts = results.get("social_posts", [])
        if social_posts:
            print("\n=== SOCIAL POSTS ===")
            for post in social_posts:
                print(f"\n{post.platform.upper()} POST:")
                print(post.content)
                print(f"Status: {post.status}")
                if post.scheduled_time:
                    print(f"Scheduled for: {post.scheduled_time}")
        
        export = results.get("export")
        if export:
            print("\n=== EXPORT ===")
            print(f"Doc URL: {export.doc_url}")
            print(f"Status: {export.status}")
            print(f"Export date: {export.export_date}")
        
        warning = results.get("warning")
        if warning:
            print(f"\n⚠️ WARNING: {warning}")

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run the content generation pipeline")
    
    parser.add_argument("--topic", type=str, help="Research topic for content generation")
    
    parser.add_argument("--start-point", type=str, choices=["research", "content", "visual", "atomization", "export", "distribution"],
                      default="research", help="Starting point in the pipeline")
    
    parser.add_argument("--item-id", type=int, help="ID of the research item or article to start from")
    
    parser.add_argument("--platforms", type=str, nargs="+", choices=["linkedin", "twitter", "medium", "substack"],
                      default=["linkedin", "twitter"], help="Social media platforms to target")
    
    parser.add_argument("--visual-types", type=str, nargs="+", choices=["chart", "infographic", "quote_card"],
                      default=["chart", "quote_card"], help="Types of visuals to generate")
    
    parser.add_argument("--reviewer-email", type=str, help="Email address of the reviewer to share with")
    
    # New arguments for review processing
    parser.add_argument("--process-review", action="store_true", help="Process a review decision")
    parser.add_argument("--export-id", type=int, help="ID of the export to review")
    parser.add_argument("--review-status", type=str, choices=["approved", "rejected", "needs_revision"], help="Review decision")
    parser.add_argument("--comments", type=str, default="", help="Review comments")
    parser.add_argument("--reviewer", type=str, help="Name of the reviewer")
    
    return parser.parse_args()

async def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Initialize database
    init_db()
    
    runner = PipelineRunner()
    
    if args.process_review:
        # Process a review
        if not all([args.export_id, args.review_status, args.reviewer]):
            print("Error: To process a review, you must provide --export-id, --review-status, and --reviewer")
            return
        
        result = await runner.process_review(
            args.export_id,
            args.review_status,
            args.comments,
            args.reviewer
        )
        
        print(f"Review processed: {result}")
        return
    
    if args.start_point == "research" and args.topic:
        # Run full pipeline
        results = await runner.run_full_pipeline(args.topic, args.platforms, args.visual_types, args.reviewer_email)
    elif args.item_id:
        # Run partial pipeline
        results = await runner.run_partial_pipeline(args.start_point, args.item_id, args.platforms, args.visual_types, args.reviewer_email)
    else:
        print("Error: You must provide either a topic (for full pipeline) or an item ID (for partial pipeline)")
        return
    
    # Display results
    runner.display_results(results)

if __name__ == "__main__":
    asyncio.run(main())
import asyncio
import logging
import os
import sys
from datetime import datetime
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("pipeline_runner")

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import agents and services
from agents.research_agent import ResearchAgent
from agents.content_agent import ContentAgent  
from agents.visual_agent import VisualAgent
from agents.atomization_agent import AtomizationAgent
from agents.distribution_agent import DistributionAgent
from services.api_clients.gemini_client import GeminiClient
from services.api_clients.google_docs_client import GoogleDocsClient
from services.api_clients.google_drive_client import GoogleDriveClient
from models.content_models import Article, Visual, ResearchItem

# User email to share documents with
USER_EMAIL = "yashdixit0885@gmail.com"

async def run_pipeline(topic: str, 
                      content_type: str = "article", 
                      tone: str = "professional",
                      visual_types: list = None):
    """
    Run the complete content generation pipeline from research to distribution.
    
    Args:
        topic (str): The topic to generate content for
        content_type (str): Type of content to generate (article, blog post, etc.)
        tone (str): Tone of the content (professional, casual, etc.)
        visual_types (list): Types of visuals to generate
    """
    try:
        logger.info(f"Starting content generation pipeline for topic: {topic}")
        start_time = datetime.now()
        
        # Initialize clients
        gemini_client = GeminiClient()
        google_docs_client = GoogleDocsClient()
        google_drive_client = GoogleDriveClient()
        
        # Step 1: Research
        logger.info("Step 1: Starting research process...")
        research_agent = ResearchAgent(gemini_client=gemini_client)
        research_data = await research_agent.run(topic)
        
        # Handle the ResearchItem object correctly
        if isinstance(research_data, ResearchItem):
            # Extract sections from meta_data if available
            sections = research_data.meta_data.get('key_topics', []) if research_data.meta_data else []
            logger.info(f"Research completed. Found {len(sections)} key topics to cover")
        else:
            # Fallback if research_data is not a ResearchItem
            logger.info("Research completed. Proceeding to content creation.")
        
        # Step 2: Content Creation
        logger.info("Step 2: Starting content creation...")
        content_agent = ContentAgent()  # ContentAgent initializes its own gemini_client
        
        # Check if research_data is a ResearchItem with an ID
        if isinstance(research_data, ResearchItem) and hasattr(research_data, 'id'):
            # Use the run method with research_item_id
            article = await content_agent.run(research_data.id)
            logger.info(f"Content creation completed. Generated {len(article.content)} characters of content")
        else:
            # Handle the case where research_data is not as expected
            logger.error("Cannot proceed: Research data doesn't have the expected format")
            raise ValueError("Research data is not in the expected format")
        
        # Step 3: Visual Generation
        logger.info("Step 3: Starting visual generation...")
        # Note: VisualAgent may have errors with generate_image, but we'll continue with the pipeline
        visual_agent = VisualAgent(
            gemini_client=gemini_client,
            google_drive_client=google_drive_client
        )
        
        # We'll try to generate visuals, but we'll handle potential errors
        try:
            visuals = await visual_agent.run(article, visual_types)
            logger.info(f"Visual generation completed. Created {len(visuals)} visuals")
        except Exception as e:
            logger.error(f"Error in visual generation: {str(e)}")
            visuals = []  # Empty list if visual generation fails
            logger.info("Continuing without visuals due to error")
        
        # Step 4: Document Creation with Integrated Visuals
        logger.info("Step 4: Creating professional document with visuals...")
        try:
            document = await google_docs_client.create_professional_document(article, visuals)
            doc_id = document.get("documentId") if isinstance(document, dict) else None
            
            # Share the document with the user if we have a document ID
            if doc_id:
                sharing_successful = google_docs_client.share_document(
                    doc_id=doc_id,
                    email=USER_EMAIL,
                    role='writer'
                )
                
                if sharing_successful:
                    logger.info(f"Document shared with {USER_EMAIL}")
                else:
                    logger.error(f"Failed to share document with {USER_EMAIL}")
                    
            logger.info(f"Document created with ID: {doc_id}")
        except Exception as e:
            logger.error(f"Error creating document: {str(e)}")
            document = {"documentId": None}
            logger.info("Continuing without document due to error")
        
        # Step 5: Content Atomization
        logger.info("Step 5: Starting content atomization...")
        atomization_agent = AtomizationAgent()  # AtomizationAgent initializes its own gemini_client
        
        # Check if article has an ID before proceeding
        if hasattr(article, 'id'):
            try:
                # Pass article_id to the run method as it expects
                atomic_content = await atomization_agent.run(article.id)
                logger.info(f"Content atomization completed. Created {len(atomic_content)} atomic content pieces")
            except Exception as e:
                logger.error(f"Error in content atomization: {str(e)}")
                atomic_content = []  # Empty list if atomization fails
                logger.info("Continuing without atomization due to error")
        else:
            logger.error("Cannot atomize: Article doesn't have an ID")
            atomic_content = []
            
        # Step 6: Distribution (can implement properly later)
        logger.info("Step 6: Preparing content for distribution...")
        # Simplified distribution for now
        distribution_results = []
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        logger.info(f"Pipeline completed in {total_time:.2f} seconds")
        
        return {
            "article": article,
            "visuals": visuals,
            "document_id": document.get("documentId") if isinstance(document, dict) else None,
            "atomic_content": atomic_content,
            "distribution_results": distribution_results,
            "total_time": total_time
        }
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        return {"error": str(e)}

async def main():
    # Example usage:
    topic = "The Impact of Artificial Intelligence on Content Creation"
    visual_types = ["header_image", "chart", "infographic", "quote_card"]
    
    result = await run_pipeline(
        topic=topic,
        content_type="article",
        tone="professional",
        visual_types=visual_types
    )
    
    if "error" not in result:
        doc_id = result.get("document_id")
        if doc_id:
            logger.info(f"Pipeline successful! Document available at: https://docs.google.com/document/d/{doc_id}")
            logger.info(f"Document has been shared with {USER_EMAIL} for access")
        else:
            logger.info("Pipeline completed with partial success (no document created)")
    else:
        logger.error(f"Pipeline failed with error: {result['error']}")
    
if __name__ == "__main__":
    asyncio.run(main())
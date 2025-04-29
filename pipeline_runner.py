import asyncio
import logging
import os
import sys
from datetime import datetime

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
from models.content_models import Article, Visual

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
        research_data = await research_agent.research(topic)
        logger.info(f"Research completed. Found {len(research_data.get('sections', []))} key sections to cover")
        
        # Step 2: Content Creation
        logger.info("Step 2: Starting content creation...")
        content_agent = ContentAgent(gemini_client=gemini_client)
        article = await content_agent.generate_content(
            research_data=research_data,
            topic=topic,
            content_type=content_type,
            tone=tone
        )
        logger.info(f"Content creation completed. Generated {len(article.content)} characters of content")
        
        # Save article to database or file system
        # For demo purposes, we'll just use the article object directly
        
        # Step 3: Visual Generation
        logger.info("Step 3: Starting visual generation...")
        visual_agent = VisualAgent(
            gemini_client=gemini_client,
            google_drive_client=google_drive_client
        )
        visuals = await visual_agent.run(article, visual_types)
        logger.info(f"Visual generation completed. Created {len(visuals)} visuals")
        
        # Step 4: Document Creation with Integrated Visuals
        logger.info("Step 4: Creating professional document with visuals...")
        document = await google_docs_client.create_professional_document(article, visuals)
        logger.info(f"Document created with ID: {document.get('documentId')}")
        
        # Step 5: Content Atomization
        logger.info("Step 5: Starting content atomization...")
        atomization_agent = AtomizationAgent(gemini_client=gemini_client)
        atomic_content = await atomization_agent.atomize(article)
        logger.info(f"Content atomization completed. Created {len(atomic_content)} atomic content pieces")
        
        # Step 6: Distribution
        logger.info("Step 6: Preparing content for distribution...")
        distribution_agent = DistributionAgent()
        distribution_results = await distribution_agent.distribute(article, atomic_content, visuals)
        logger.info(f"Content distribution prepared for {len(distribution_results)} platforms")
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        logger.info(f"Pipeline completed in {total_time:.2f} seconds")
        
        return {
            "article": article,
            "visuals": visuals,
            "document_id": document.get("documentId"),
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
        logger.info(f"Pipeline successful! Document available at: https://docs.google.com/document/d/{result['document_id']}")
    else:
        logger.error(f"Pipeline failed with error: {result['error']}")
    
if __name__ == "__main__":
    asyncio.run(main()) 
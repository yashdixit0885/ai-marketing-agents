from .base_agent import BaseAgent
from services.api_clients.gemini_client import GeminiClient
from models.content_models import Article, ResearchItem
from models import db_session

class ContentAgent(BaseAgent):
    """Agent responsible for creating long-form content."""
    
    def __init__(self):
        super().__init__("Content Agent", "Creates comprehensive articles based on research")
        self.gemini_client = GeminiClient()
    
    async def run(self, research_item_id):
        """Generate an article based on the research item."""
        self.log_status(f"Starting article generation for research item: {research_item_id}")
        
        # Retrieve the research item
        research_item = db_session.query(ResearchItem).get(research_item_id)
        if not research_item:
            raise ValueError(f"Research item with ID {research_item_id} not found")
        
        # Generate article content
        article_content = await self._generate_article(research_item)
        
        # Process and store the article
        article = await self.process({
            "research_item": research_item,
            "content": article_content
        })
        
        self.log_status(f"Completed article generation: {article.title}")
        return article
    
    async def _generate_article(self, research_item):
        """Generate article content using Gemini."""
        prompt = f"""
        Based on the following research:
        {research_item.content}
        
        Create a comprehensive 1000-word article about this topic.
        
        The article should include:
        1. An engaging introduction with a hook
        2. Clear problem statement
        3. Analysis of AI solutions
        4. Case studies or examples
        5. Implementation guide
        6. ROI considerations
        7. Future outlook
        8. Conclusion with key takeaways
        
        Format the article with proper headings and subheadings.
        Ensure the content is factual, insightful, and professionally written.
        """
        
        response = await self.gemini_client.generate_content(prompt)
        return response
    
    async def process(self, data):
        """Process and store the article."""
        research_item = data["research_item"]
        content = data["content"]
        
        # Extract title from the first line of content
        title_line = content.split('\n')[0]
        title = title_line.replace('#', '').strip()
        
        # Create the article
        article = Article(
            title=title,
            content=content,
            status="draft",
            word_count=len(content.split())
        )
        
        # Link to research item
        article.research_items.append(research_item)
        
        db_session.add(article)
        db_session.commit()
        
        return article
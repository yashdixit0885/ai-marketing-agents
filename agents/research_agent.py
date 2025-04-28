import json
from .base_agent import BaseAgent
from services.api_clients.gemini_client import GeminiClient
from models.content_models import ResearchItem
from models import db_session

class ResearchAgent(BaseAgent):
    """Agent responsible for conducting research on AI topics."""
    
    def __init__(self):
        super().__init__("Research Agent", "Conducts deep research on AI business applications")
        self.gemini_client = GeminiClient()
    
    async def run(self, topic):
        """Run research on the given topic."""
        self.log_status(f"Starting research on topic: {topic}")
        
        # Get research plan from Gemini
        research_plan = await self._create_research_plan(topic)
        
        # Collect data from various sources
        data = await self._collect_data(topic, research_plan)
        
        # Process and store research results
        processed_data = await self.process(data)
        
        self.log_status(f"Completed research on topic: {topic}")
        return processed_data
    
    async def _create_research_plan(self, topic):
        """Create a research plan using Gemini."""
        prompt = f"""
        Create a detailed research plan for gathering information about: {topic}
        
        The plan should include:
        1. Key subtopics to explore
        2. Specific questions to answer
        3. Important data points to collect
        4. Types of sources to prioritize
        
        Format the response as a JSON object.
        """
        
        response = await self.gemini_client.generate_content(prompt)
        return json.loads(response)
    
    async def _collect_data(self, topic, research_plan):
        """Collect data from various sources based on the research plan."""
        # This would connect to various APIs and data sources
        # For now, we'll use Gemini to simulate data collection
        
        prompt = f"""
        Based on this research plan:
        {json.dumps(research_plan, indent=2)}
        
        Generate comprehensive research findings about: {topic}
        
        Include:
        - Key insights from academic papers
        - Recent industry developments
        - Case studies and examples
        - Expert opinions
        - Statistics and data points
        
        Format the response as a detailed research report with sections.
        """
        
        response = await self.gemini_client.generate_content(prompt)
        return response
    
    async def process(self, data):
        """Process and store the research data."""
        # Extract key information and store in the database
        # This is simplified; in reality you'd parse the data more thoroughly
        
        # Example: Create a research item in the database
        research_item = ResearchItem(
            title="Research on AI topic",
            source="Gemini Research Agent",
            content=data,
            metadata={"source_type": "ai_generated"}
        )
        
        db_session.add(research_item)
        db_session.commit()
        
        return research_item
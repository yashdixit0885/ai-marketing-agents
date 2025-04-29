from .base_agent import BaseAgent
from services.api_clients.gemini_client import GeminiClient
from models.content_models import Article, ResearchItem
from models import db_session
import json
import re

class ContentAgent(BaseAgent):
    """Agent responsible for creating long-form content."""
    
    def __init__(self):
        super().__init__("Content Agent", "Creates comprehensive articles based on research")
        self.gemini_client = GeminiClient()
    
    async def run(self, research_item_id):
        """Generate an article based on the research item."""
        self.log_status(f"Starting article generation for research item: {research_item_id}")
        
        # Retrieve the research item
        research_item = db_session.get(ResearchItem, research_item_id)
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
        """Generate higher-quality article content using Gemini."""
        # Analyze the research content to determine the best article structure
        analysis_prompt = f"""
        Analyze this research content and determine the optimal article structure:
        {research_item.content[:1500]}...
        
        Identify:
        1. The primary audience (technical, business, general)
        2. The most compelling hooks or insights
        3. The 3-5 key points that should be highlighted
        4. Any statistics or case studies that should be featured
        5. Any areas where visuals would be particularly effective
        
        Provide your analysis in JSON format.
        """
        
        analysis = await self.gemini_client.generate_content(analysis_prompt)
        try:
            structure = json.loads(analysis)
        except:
            # Fallback if JSON parsing fails
            structure = {
                "audience": "business",
                "hooks": ["The transformative potential of AI"],
                "key_points": ["Cost savings", "Efficiency gains", "Implementation challenges", "Future outlook"],
                "featured_stats": ["ROI metrics", "Adoption rates"],
                "visual_opportunities": ["Process comparison", "ROI chart", "Implementation timeline"]
            }
        
        # Create an audience-specific article template
        templates = {
            "technical": """
                # [TITLE]
                
                ## Introduction
                [Technical context and significance]
                
                ## Technical Background
                [Core concepts and principles]
                
                ## Current State of the Art
                [Latest developments and innovations]
                
                ## Implementation Architecture
                [System design and technical requirements]
                
                ## Performance Analysis
                [Metrics, benchmarks, and comparisons]
                
                ## Challenges and Solutions
                [Technical hurdles and approaches]
                
                ## Future Directions
                [Emerging research and potential advances]
                
                ## Conclusion
                [Summary and implications]
            """,
            "business": """
                # [TITLE]
                
                ## Executive Summary
                [Business context and value proposition]
                
                ## The Business Case
                [Problem statement and market opportunity]
                
                ## Strategic Advantages
                [Competitive benefits and organizational impact]
                
                ## Implementation Roadmap
                [Process, timeline, and requirements]
                
                ## ROI Analysis
                [Cost-benefit analysis and expected returns]
                
                ## Case Studies
                [Real-world examples and outcomes]
                
                ## Best Practices
                [Guidelines for successful implementation]
                
                ## Conclusion
                [Key takeaways and next steps]
            """,
            "general": """
                # [TITLE]
                
                ## Introduction
                [Engaging hook and topic relevance]
                
                ## Understanding the Basics
                [Simplified explanation of key concepts]
                
                ## Real-World Applications
                [Practical examples and use cases]
                
                ## Benefits and Opportunities
                [Advantages and positive impacts]
                
                ## Challenges and Considerations
                [Potential hurdles and ethical questions]
                
                ## Looking Ahead
                [Future trends and possibilities]
                
                ## Conclusion
                [Summary and significance]
            """
        }
        
        # Select the appropriate template based on audience
        audience = structure.get("audience", "business")
        template = templates.get(audience, templates["business"])
        
        # Create a hook based on the identified compelling insights
        hooks = structure.get("hooks", ["The transformative potential of AI"])
        hook = hooks[0] if hooks else "The transformative potential of AI"
        
        # Generate the article using the structured template
        prompt = f"""
        Based on this research:
        {research_item.content}
        
        Create a comprehensive article using this structure:
        {template}
        
        The article should:
        1. Begin with a compelling hook related to: {hook}
        2. Focus on these key points: {structure.get("key_points", ["Key insights"])}
        3. Highlight these statistics or examples: {structure.get("featured_stats", ["Relevant statistics"])}
        4. Include opportunities for visuals related to: {structure.get("visual_opportunities", ["Relevant visuals"])}
        5. Maintain a professional, authoritative tone appropriate for a {audience} audience
        6. Include proper citations and references
        7. Have an engaging, specific title (not generic)
        
        Format the article with proper markdown headings, bullet points, and emphasis where appropriate.
        Aim for approximately 1500-2000 words with well-balanced sections.
        """
        
        response = await self.gemini_client.generate_content(prompt)
        
        # Verify the quality of the generated article
        verification_prompt = f"""
        Review this article for quality, completeness, and adherence to guidelines:
        {response[:1500]}...
        
        Check for:
        1. An engaging, specific title
        2. Proper section structure following the template
        3. In-depth treatment of key points
        4. Clear explanations and examples
        5. Professional tone appropriate for the audience
        6. Proper citations and references
        
        If improvements are needed, specify exactly what should be fixed.
        If the quality is good, respond with "QUALITY_SATISFACTORY".
        """
        
        verification = await self.gemini_client.generate_content(verification_prompt)
        
        # If quality issues are identified, revise the article
        if "QUALITY_SATISFACTORY" not in verification:
            revision_prompt = f"""
            Revise this article to address these quality issues:
            {verification}
            
            Here is the current article:
            {response}
            
            Provide an improved version that addresses all the identified issues.
            """
            response = await self.gemini_client.generate_content(revision_prompt)
        
        return response
    
    async def process(self, data):
        """Process and store the article with enhanced metadata."""
        research_item = data["research_item"]
        content = data["content"]
        
        # Extract title from the first line of content
        lines = content.split('\n')
        title = ""
        for line in lines:
            line = line.strip()
            if line and line.startswith('#'):
                title = line.replace('#', '').strip()
                break
        
        # If no title found in the content, use a default
        if not title:
            title = f"Article on {research_item.title}"
        
        # Count words
        word_count = len(content.split())
        
        # Extract headings for structure analysis
        headings = []
        for line in lines:
            line = line.strip()
            if line.startswith('##') and not line.startswith('###'):
                heading = line.replace('##', '').strip()
                headings.append(heading)
        
        # Create the article
        article = Article(
            title=title,
            content=content,
            status="draft",
            word_count=word_count,
            metadata={
                "structure": headings,
                "research_source": research_item.title,
                "audience": "business"  # Default, could be extracted from analysis
            }
        )
        
        # Link to research item
        article.research_items.append(research_item)
        
        db_session.add(article)
        db_session.commit()
        
        return article
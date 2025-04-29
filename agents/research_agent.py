import json
import re
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
        """Create a more sophisticated research plan using Gemini."""
        # Identify topic category
        topic_categories = ["ai_ethics", "business_automation", "healthcare_ai", 
                            "ai_development", "industry_specific"]
        
        # Create topic-specific prompts
        category_prompts = {
            "ai_ethics": """
                Create a research plan for gathering comprehensive information about ethical considerations in AI: {topic}
                
                Focus on:
                1. Recent regulatory developments and frameworks
                2. Real-world ethical dilemmas and case studies
                3. Industry standards and best practices
                4. Contrasting perspectives from different stakeholders
                5. Future ethical challenges and proposed solutions
                
                Format as JSON with subtopics, questions, data points, and prioritized sources.
            """,
            "business_automation": """
                Create a research plan for gathering comprehensive information about AI business automation: {topic}
                
                Focus on:
                1. ROI metrics and business case studies
                2. Implementation challenges and solutions
                3. Required technical infrastructure
                4. Change management best practices
                5. Future trends and competitive advantages
                
                Format as JSON with subtopics, questions, data points, and prioritized sources.
            """,
            "healthcare_ai": """
                Create a research plan for gathering comprehensive information about AI in healthcare: {topic}
                
                Focus on:
                1. Clinical applications and outcomes
                2. Regulatory considerations and approvals
                3. Patient privacy and data security
                4. Integration with existing healthcare systems
                5. Cost-benefit analysis for healthcare providers
                
                Format as JSON with subtopics, questions, data points, and prioritized sources.
            """,
            "ai_development": """
                Create a research plan for gathering comprehensive information about AI development: {topic}
                
                Focus on:
                1. Latest technical approaches and algorithms
                2. Hardware and infrastructure requirements
                3. Development frameworks and tools
                4. Performance benchmarks and evaluation methods
                5. Current limitations and research frontiers
                
                Format as JSON with subtopics, questions, data points, and prioritized sources.
            """,
            "industry_specific": """
                Create a research plan for gathering comprehensive information about industry-specific AI applications: {topic}
                
                Focus on:
                1. Industry-specific use cases and applications
                2. Implementation challenges unique to this industry
                3. Competitive landscape and leading providers
                4. Integration with existing industry systems
                5. Industry-specific ROI metrics and success stories
                
                Format as JSON with subtopics, questions, data points, and prioritized sources.
            """
        }
        
        # Identify the most relevant category
        prompt = f"""
        Identify the most relevant category for the topic: {topic}
        Categories: {', '.join(topic_categories)}
        Return only the category name as a single word.
        """
        
        category_response = await self.gemini_client.generate_content(prompt)
        category = category_response.strip().lower()
        if category not in category_prompts:
            category = "general"  # Default category
        
        # Get the appropriate research plan template
        research_prompt = category_prompts.get(
            category,
            """
            Create a detailed research plan for gathering information about: {topic}
            
            The plan should include:
            1. Key subtopics to explore (minimum 5)
            2. Specific questions to answer for each subtopic (minimum 3 per subtopic)
            3. Important data points to collect
            4. Types of sources to prioritize
            5. Potential experts or organizations to reference
            
            Format the response as a JSON object.
            """
        ).format(topic=topic)
        
        # Generate the research plan
        response = await self.gemini_client.generate_content(research_prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            self.log_status(f"Error parsing JSON: {e}")
            # More sophisticated fallback plan
            return {
                "key_subtopics": [
                    "Core technologies and concepts",
                    "Recent developments and innovations",
                    "Business applications and use cases",
                    "Implementation challenges and solutions",
                    "Future outlook and trends"
                ],
                "specific_questions": {
                    "Core technologies": [
                        "What are the fundamental principles of this technology?",
                        "How has it evolved over time?",
                        "What are the key components or methodologies?"
                    ],
                    "Recent developments": [
                        "What breakthroughs have occurred in the last 1-2 years?",
                        "Which organizations are leading innovation in this area?",
                        "How have these developments changed the technology landscape?"
                    ],
                    "Business applications": [
                        "What are the primary use cases for businesses?",
                        "Which industries are seeing the most benefit?",
                        "What ROI metrics are being reported?"
                    ],
                    "Implementation challenges": [
                        "What are the common obstacles to implementation?",
                        "How are organizations overcoming these challenges?",
                        "What resources are required for successful deployment?"
                    ],
                    "Future outlook": [
                        "What are the predicted trends for the next 3-5 years?",
                        "What potential disruptions might emerge?",
                        "How will this technology evolve and integrate with others?"
                    ]
                },
                "important_data_points": [
                    "Market size and growth rate",
                    "Key performance metrics and benchmarks",
                    "Adoption rates across industries",
                    "Cost-benefit analyses",
                    "Success and failure statistics"
                ],
                "sources_to_prioritize": [
                    "Academic research papers",
                    "Industry reports and white papers",
                    "Case studies from leading organizations",
                    "Expert interviews and thought leadership",
                    "Regulatory and policy documents"
                ]
            }
    
    async def _collect_data(self, topic, research_plan):
        """Collect data from various sources with source validation."""
        # Extract key questions from research plan
        questions = []
        for subtopic, subtopic_questions in research_plan.get("specific_questions", {}).items():
            questions.extend(subtopic_questions)
        
        # If questions are not in expected format, extract them differently
        if not questions and isinstance(research_plan.get("specific_questions"), list):
            questions = research_plan.get("specific_questions", [])
        
        # Ensure we have at least some questions
        if not questions:
            questions = [
                f"What is {topic} and why is it important?",
                f"What are the latest developments in {topic}?",
                f"How is {topic} being implemented in businesses?",
                f"What challenges exist with {topic}?",
                f"What is the future outlook for {topic}?"
            ]
        
        # Generate comprehensive research findings
        prompt = f"""
        Based on this research plan:
        {json.dumps(research_plan, indent=2)}
        
        Generate comprehensive research findings about: {topic}
        
        Your response must include:
        1. An executive summary of key findings (maximum 250 words)
        2. Detailed analysis for each subtopic, addressing all research questions
        3. Supporting evidence including:
           - Statistics and data points with sources
           - Expert perspectives with attributions
           - Case studies with measurable outcomes
           - Contrasting viewpoints where relevant
        4. A "Key Insights" section that extracts the most valuable information
        5. A properly formatted references section
        
        Format as a structured research report with clear headings and sections.
        Ensure all facts are supported with evidence and proper attribution.
        """
        
        # Get initial research
        response = await self.gemini_client.generate_content(prompt)
        
        # Validate the research quality
        validation_prompt = f"""
        Review this research report on {topic} and assess its quality:
        {response[:1000]}...
        
        Identify any areas that need improvement:
        1. Is it comprehensive and well-structured?
        2. Does it provide specific, actionable insights?
        3. Does it include relevant statistics and data points?
        4. Does it reference specific sources and experts?
        5. Does it consider multiple perspectives?
        
        If improvements are needed, specify exactly what's missing.
        If the quality is good, respond with "QUALITY_SATISFACTORY".
        """
        
        validation_response = await self.gemini_client.generate_content(validation_prompt)
        
        # If quality issues are identified, enhance the research
        if "QUALITY_SATISFACTORY" not in validation_response:
            enhancement_prompt = f"""
            Enhance this research report on {topic} by addressing these quality issues:
            {validation_response}
            
            Here is the current report:
            {response}
            
            Provide an improved version that addresses all the identified issues.
            """
            response = await self.gemini_client.generate_content(enhancement_prompt)
        
        return response
    
    async def process(self, data):
        """Process and store the research data with enhanced metadata."""
        # Extract key information
        
        # Extract title from the content (assuming first line is title)
        lines = data.split('\n')
        title_line = ""
        for line in lines[:10]:  # Check first 10 lines for a title
            if line.strip() and (line.startswith('#') or len(line) < 100):
                title_line = line.strip().replace('#', '').strip()
                break
        
        # If no title found, create one
        if not title_line:
            title_line = "Research on AI Topic"
        
        # Extract key topics using simple regex patterns
        topics = []
        topic_patterns = [
            r'(?:key|main|primary|important)\s+(?:topic|aspect|area|consideration)s?[:\s]+([^\.]+)',
            r'(?:key|main|primary|important)\s+(?:finding|insight|discovery)s?[:\s]+([^\.]+)',
            r'(?:In summary|To summarize|In conclusion)[,:\s]+([^\.]+)'
        ]
        
        for pattern in topic_patterns:
            matches = re.findall(pattern, data, re.IGNORECASE)
            topics.extend(matches)
        
        # Limit to 5 topics
        topics = topics[:5]
        
        # Extract stats and figures using regex
        stats = []
        stat_patterns = [
            r'(\d+(?:\.\d+)?%)',  # Percentages
            r'(\$\d+(?:\.\d+)?(?:\s*(?:million|billion|trillion)))',  # Dollar amounts
            r'(\d+(?:\.\d+)?(?:\s*(?:million|billion|trillion)))'  # Large numbers
        ]
        
        for pattern in stat_patterns:
            matches = re.findall(pattern, data, re.IGNORECASE)
            stats.extend(matches)
        
        # Limit to 10 stats
        stats = stats[:10]
        
        # Create metadata
        meta_data = {
            "source_type": "ai_generated",
            "key_topics": topics,
            "statistics": stats,
            "word_count": len(data.split())
        }
        
        # Example: Create a research item in the database
        research_item = ResearchItem(
            title=title_line,
            source="Gemini Research Agent",
            content=data,
            meta_data=meta_data
        )
        
        db_session.add(research_item)
        db_session.commit()
        
        return research_item
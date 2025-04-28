import json
import re
from .base_agent import BaseAgent
from services.api_clients.gemini_client import GeminiClient
from models.content_models import Article, SocialPost
from models import db_session

class AtomizationAgent(BaseAgent):
    """Agent responsible for extracting and formatting content for social media."""
    
    def __init__(self):
        super().__init__("Atomization Agent", "Extracts content for social media")
        self.gemini_client = GeminiClient()
    
    async def run(self, article_id, platforms=None):
        """Generate social media content for an article."""
        self.log_status(f"Starting content atomization for article: {article_id}")
        
        if platforms is None:
            platforms = ["linkedin", "twitter", "medium", "substack"]
        
        # Retrieve the article
        article = db_session.query(Article).get(article_id)
        if not article:
            raise ValueError(f"Article with ID {article_id} not found")
        
        # Generate content for each platform
        social_posts = []
        for platform in platforms:
            content = await self._generate_platform_content(article, platform)
            
            # Process and store the social post
            social_post = await self.process({
                "article": article,
                "content": content,
                "platform": platform
            })
            
            social_posts.append(social_post)
        
        self.log_status(f"Completed content atomization for article: {article_id}")
        return social_posts
    
    async def _generate_platform_content(self, article, platform):
        """Generate content specific to a social media platform."""
        if platform == "linkedin":
            return await self._generate_linkedin_content(article)
        elif platform == "twitter":
            return await self._generate_twitter_content(article)
        elif platform == "medium":
            return await self._generate_medium_content(article)
        elif platform == "substack":
            return await self._generate_substack_content(article)
        else:
            raise ValueError(f"Unsupported platform: {platform}")
    
    async def _generate_linkedin_content(self, article):
        """Generate LinkedIn post content (200 words)."""
        prompt = f"""
        Create a LinkedIn post (approximately 200 words) based on this article:
        {article.content[:3000]}  # Limit content to avoid token limits
        
        The post should:
        1. Start with a key insight or hook
        2. Include 2-3 bullet points of main takeaways
        3. End with a call-to-action
        4. Include a link to the full article
        5. Add 3-5 relevant hashtags
        
        Format properly for LinkedIn with line breaks and emojis where appropriate.
        """
        
        response = await self.gemini_client.generate_content(prompt)
        return response
    
    async def _generate_twitter_content(self, article):
        """Generate Twitter content (280 characters max)."""
        prompt = f"""
        Create a Twitter post (max 280 characters) based on this article:
        {article.title}
        
        The tweet should:
        1. Include a single powerful insight or statistic
        2. Be engaging and encourage clicks
        3. Include a link placeholder [LINK]
        4. Use 1-2 relevant hashtags
        
        Keep the entire tweet under 280 characters including the [LINK] placeholder.
        """
        
        response = await self.gemini_client.generate_content(prompt)
        tweet = response.strip()
        
        # Ensure the tweet is under 280 characters
        if len(tweet) > 280:
            tweet = tweet[:277] + "..."
        
        return tweet
    
    async def _generate_medium_content(self, article):
        """Generate Medium post summary/intro."""
        prompt = f"""
        Create a Medium post intro based on this article:
        {article.title}
        
        The intro should:
        1. Be approximately 100 words
        2. Introduce the topic with an engaging hook
        3. Hint at what readers will learn
        4. Set up the structure for the full article
        
        This will be used as the introduction to the full article on Medium.
        """
        
        response = await self.gemini_client.generate_content(prompt)
        return response
    
    async def _generate_substack_content(self, article):
        """Generate Substack newsletter content."""
        prompt = f"""
        Create a Substack newsletter intro based on this article:
        {article.title}
        
        The newsletter intro should:
        1. Be approximately 150 words
        2. Start with an engaging greeting
        3. Introduce the topic with a personal tone
        4. Explain why this topic matters to the readers
        5. Preview what's included in the full article
        
        This will be used as the introduction to the full article in a newsletter.
        """
        
        response = await self.gemini_client.generate_content(prompt)
        return response
    
    async def process(self, data):
        """Process and store the social post."""
        article = data["article"]
        content = data["content"]
        platform = data["platform"]
        
        # Create the social post
        social_post = SocialPost(
            platform=platform,
            content=content,
            status="draft",
            article_id=article.id
        )
        
        db_session.add(social_post)
        db_session.commit()
        
        return social_post
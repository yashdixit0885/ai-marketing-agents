import json
import re
from datetime import datetime
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
        article = db_session.get(Article, article_id)
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
        """Generate high-quality LinkedIn post content."""
        # Extract key talking points first
        talking_points_prompt = f"""
        Analyze this article and extract the 3 most compelling talking points for a professional LinkedIn audience:
        {article.content[:3000]}
        
        For each talking point:
        1. Identify a key insight that would resonate with business professionals
        2. Find a supporting statistic or example from the article
        3. Suggest how this could be framed as valuable professional knowledge
        
        Format as a JSON array with 3 items, each with 'insight', 'support', and 'value' fields.
        """
        
        talking_points_response = await self.gemini_client.generate_content(talking_points_prompt)
        
        try:
            talking_points = json.loads(talking_points_response)
        except:
            # Fallback for parsing error
            talking_points = [
                {"insight": "AI can significantly improve operational efficiency", 
                 "support": "Companies implementing AI report 30% efficiency gains on average", 
                 "value": "This means potential cost savings while improving output quality"}
            ]
        
        # Generate the LinkedIn post
        prompt = f"""
        Create a professional LinkedIn post based on this article:
        {article.content[:2500]}
        
        Using these key talking points:
        {json.dumps(talking_points, indent=2)}
        
        The post should:
        1. Start with a thought-provoking hook or question that addresses a business challenge
        2. Include a personal perspective that would resonate with business professionals
        3. Present the key insights in a structured, scannable format with emojis
        4. Highlight specific statistics or examples that demonstrate business value
        5. End with a clear call-to-action that encourages professional engagement
        6. Include line breaks for readability and white space
        7. Add 3-5 relevant industry hashtags at the end
        
        Keep the post around 200 words and maintain a professional yet conversational tone.
        DO NOT use overly promotional language or clickbait.
        """
        
        response = await self.gemini_client.generate_content(prompt)
        
        # Verify the quality
        verification_prompt = f"""
        Evaluate this LinkedIn post for professional quality:
        {response}
        
        Check for:
        1. Professional tone appropriate for business audience
        2. Clear structure with proper line breaks
        3. Presence of key insights from the talking points
        4. A compelling hook that would drive engagement
        5. Appropriate use of emojis (not excessive)
        6. Relevant hashtags
        7. A clear call to action
        
        If improvements are needed, respond with specific issues.
        If the quality is good, respond with "QUALITY_SATISFACTORY".
        """
        
        verification = await self.gemini_client.generate_content(verification_prompt)
        
        if "QUALITY_SATISFACTORY" not in verification:
            revision_prompt = f"""
            Revise this LinkedIn post based on this feedback:
            {verification}
            
            Original post:
            {response}
            
            Ensure the revised post has:
            - Professional tone
            - Clear structure with line breaks
            - Compelling hook
            - Key insights clearly presented
            - Appropriate emojis
            - Relevant hashtags
            - Clear call to action
            
            Keep around 200 words.
            """
            
            response = await self.gemini_client.generate_content(revision_prompt)
        
        return response
    
    async def _generate_twitter_content(self, article):
        """Generate high-quality Twitter content with thread options."""
        # Extract key insights
        insights_prompt = f"""
        Extract the single most compelling insight from this article that would work well in a tweet:
        {article.title}
        {article.content[:1000]}
        
        The insight should:
        1. Be surprising or counter-intuitive
        2. Contain a specific statistic or fact if possible
        3. Be relevant to business or technology professionals
        4. Be expressible in under 200 characters
        
        Provide just the insight, no additional commentary.
        """
        
        insight = await self.gemini_client.generate_content(insights_prompt)
        
        # Generate primary tweet
        prompt = f"""
        Create a compelling tweet based on this key insight:
        {insight}
        
        The tweet should:
        1. Start with a powerful hook or question
        2. Present the key insight clearly
        3. Use concise, impactful language
        4. Include a [LINK] placeholder
        5. Use 1-2 relevant hashtags
        6. Optionally include a simple emoji if appropriate
        
        Keep the entire tweet under 280 characters including the [LINK] placeholder.
        Format the tweet for Twitter without any additional text or explanation.
        """
        
        response = await self.gemini_client.generate_content(prompt)
        
        # Check character count and adjust if needed
        tweet = response.strip()
        if len(tweet) > 280:
            # Shorten the tweet while preserving core message
            shortening_prompt = f"""
            This tweet is over the 280 character limit:
            {tweet}
            
            Create a shortened version that:
            1. Preserves the core insight
            2. Maintains the [LINK] placeholder
            3. Keeps at least one hashtag
            4. Is under 260 characters total
            
            Provide just the tweet, no explanation.
            """
            
            tweet = await self.gemini_client.generate_content(shortening_prompt)
            tweet = tweet.strip()
            
            # Final length check
            if len(tweet) > 280:
                tweet = tweet[:277] + "..."
        
        # Generate thread options (additional tweets)
        thread_prompt = f"""
        Create 2 follow-up tweets that would work as a thread with this main tweet:
        {tweet}
        
        Based on this article:
        {article.title}
        
        Each follow-up tweet should:
        1. Be under 280 characters
        2. Add new information not in the first tweet
        3. Maintain the same tone and style
        4. Not repeat the hashtags from the first tweet
        
        Format as a JSON array with 2 tweet objects, each with 'text' field only.
        """
        
        thread_response = await self.gemini_client.generate_content(thread_prompt)
        
        try:
            thread_tweets = json.loads(thread_response)
            # Format into a structured response
            result = {
                "main_tweet": tweet,
                "thread_options": [t.get('text', '') for t in thread_tweets]
            }
            return result
        except:
            # If JSON parsing fails, return just the main tweet
            return tweet
    
    async def _generate_medium_content(self, article):
        """Generate high-quality Medium post intro and outline."""
        # Analyze article for key themes
        analysis_prompt = f"""
        Analyze this article to identify the central themes and key points for a Medium audience:
        {article.title}
        {article.content[:2000]}
        
        Identify:
        1. The main premise or argument
        2. 3-5 key supporting points
        3. A potential hook that would engage Medium readers
        4. The overall tone that would work best (authoritative, conversational, narrative, etc.)
        
        Format as JSON with 'premise', 'key_points', 'hook', and 'tone' fields.
        """
        
        analysis_response = await self.gemini_client.generate_content(analysis_prompt)
        
        try:
            analysis = json.loads(analysis_response)
        except:
            # Fallback if parsing fails
            analysis = {
                "premise": "AI is transforming business operations across industries",
                "key_points": ["Efficiency gains", "Cost reduction", "New capabilities", "Implementation challenges"],
                "hook": "While everyone talks about AI disruption, the real story is happening behind the scenes",
                "tone": "authoritative but accessible"
            }
        
        # Generate Medium intro
        intro_prompt = f"""
        Create a compelling Medium post introduction based on this analysis:
        {json.dumps(analysis, indent=2)}
        
        The introduction should:
        1. Start with the identified hook to immediately engage readers
        2. Introduce the main premise clearly
        3. Hint at the key points that will be covered
        4. Establish the appropriate tone ({analysis.get('tone', 'authoritative but accessible')})
        5. End with a smooth transition to the main content
        
        Write approximately 200 words, formatted in the Medium style with:
        - Short, punchy paragraphs
        - Strategic use of italics for emphasis
        - One rhetorical question to engage readers
        - Clear value proposition for why this article matters
        
        Format with proper Markdown, including emphasis where appropriate.
        """
        
        intro = await self.gemini_client.generate_content(intro_prompt)
        
        # Generate article outline for the full Medium post
        outline_prompt = f"""
        Create an outline for a full Medium article that would follow this introduction:
        {intro}
        
        Based on these key points:
        {json.dumps(analysis.get('key_points', []), indent=2)}
        
        The outline should include:
        1. Section headings (formatted as H2)
        2. Brief description of each section (1-2 sentences)
        3. A logical flow from the introduction to a satisfying conclusion
        4. Places where examples, data, or visuals should be highlighted
        
        Format with proper Markdown for headings and structure.
        Keep the entire outline under 400 words.
        """
        
        outline = await self.gemini_client.generate_content(outline_prompt)
        
        # Combine intro and outline
        result = {
            "intro": intro,
            "outline": outline,
            "title_options": [
                article.title,  # Original title
                analysis.get("hook", "The Future of AI"),  # Hook as potential title
                f"The {analysis.get('key_points', ['Important'])[0]} of {article.title.split(':')[0] if ':' in article.title else article.title}"  # Variation
            ]
        }
        
        return result
    
    async def _generate_substack_content(self, article):
        """Generate high-quality Substack newsletter content."""
        # Analyze article for newsletter adaptation
        analysis_prompt = f"""
        Analyze this article and identify how it should be adapted for a Substack newsletter:
        {article.title}
        {article.content[:2000]}
        
        Identify:
        1. The main value proposition for newsletter subscribers
        2. The most interesting/surprising elements that would drive opens
        3. How the content should be structured for a newsletter format
        4. A compelling subject line that would maximize open rates
        
        Format as JSON with 'value_prop', 'key_elements', 'structure', and 'subject_lines' (array with 3 options) fields.
        """
        
        analysis_response = await self.gemini_client.generate_content(analysis_prompt)
        
        try:
            analysis = json.loads(analysis_response)
        except:
            # Fallback if parsing fails
            analysis = {
                "value_prop": "Understand the latest AI trends and how they impact your business",
                "key_elements": ["Industry insights", "Practical implementation advice", "Future outlook"],
                "structure": "Brief introduction, key takeaways, expanded insights, action items",
                "subject_lines": [
                    f"[New] {article.title}",
                    "The AI insights you need this week",
                    "Are you missing this AI opportunity?"
                ]
            }
        
        # Generate the newsletter intro
        intro_prompt = f"""
        Create a compelling Substack newsletter introduction based on this analysis:
        {json.dumps(analysis, indent=2)}
        
        The newsletter intro should:
        1. Start with a warm, personal greeting
        2. Present the main value proposition immediately
        3. Create intrigue about the content that follows
        4. Establish a conversational but authoritative tone
        5. Be approximately 150-200 words
        
        Format with proper Markdown including emphasis where appropriate.
        Include appropriate line breaks for readability.
        """
        
        intro = await self.gemini_client.generate_content(intro_prompt)
        
        # Generate the newsletter body structure
        body_prompt = f"""
        Create a structure for the main newsletter body that would follow this introduction:
        {intro}
        
        Based on this article:
        {article.title}
        
        The newsletter body should:
        1. Break down complex topics into digestible sections
        2. Include bullet points for key takeaways
        3. Incorporate one or two pull quotes or highlighted insights
        4. End with actionable next steps for the reader
        
        Provide section headers and brief descriptions of what each section would contain.
        Format with proper Markdown for headings and structure.
        """
        
        body_structure = await self.gemini_client.generate_content(body_prompt)
        
        # Combine all elements
        result = {
            "subject_lines": analysis.get("subject_lines", [f"[New] {article.title}"]),
            "intro": intro,
            "body_structure": body_structure,
            "full_adaptation_notes": f"This newsletter should maintain a conversational tone and focus on the {analysis.get('value_prop', 'key insights')}. Break up text with subheadings and consider adding custom visuals to illustrate key points."
        }
        
        return result
    
    async def process(self, data):
        """Process and store the social post with enhanced metadata."""
        article = data["article"]
        content = data["content"]
        platform = data["platform"]
        
        # Create metadata based on content and platform
        metadata = {
            "creation_date": datetime.now().isoformat(),
            "platform": platform,
            "article_title": article.title
        }
        
        # Add platform-specific metadata
        if platform == "twitter":
            if isinstance(content, dict):
                metadata["has_thread"] = True
                metadata["thread_length"] = len(content.get("thread_options", [])) + 1
                metadata["character_count"] = len(content.get("main_tweet", ""))
            else:
                metadata["has_thread"] = False
                metadata["character_count"] = len(content)
        
        elif platform == "linkedin":
            # Extract hashtags
            hashtags = re.findall(r'(#\w+)', content)
            metadata["hashtags"] = hashtags
            metadata["word_count"] = len(content.split())
        
        elif platform == "medium":
            if isinstance(content, dict):
                metadata["has_outline"] = True
                metadata["title_options"] = content.get("title_options", [])
                metadata["intro_word_count"] = len(content.get("intro", "").split())
            else:
                metadata["has_outline"] = False
                metadata["word_count"] = len(content.split())
        
        elif platform == "substack":
            if isinstance(content, dict):
                metadata["subject_line_options"] = content.get("subject_lines", [])
            metadata["word_count"] = len(str(content).split())
        
        # Serialize content if it's a dictionary
        content_to_store = json.dumps(content) if isinstance(content, dict) else content
        
        # Create the social post
        social_post = SocialPost(
            platform=platform,
            content=content_to_store,
            status="draft",
            article_id=article.id,
            metadata=metadata
        )
        
        db_session.add(social_post)
        db_session.commit()
        
        return social_post
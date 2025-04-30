import os
import json
import asyncio
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import logging
from typing import List, Dict, Any, Optional, Tuple
import re
from sqlalchemy.orm import Session
import time
import tempfile

from .base_agent import BaseAgent
from services.api_clients.gemini_client import GeminiClient
from services.api_clients.google_drive_client import GoogleDriveClient
from services.api_clients.stable_diffusion_client import StableDiffusionClient
from services.api_clients.huggingface_client import HuggingFaceClient
from models.content_models import Visual, Article, VisualType
from models import db_session
from utils.agent_metrics import timed_step
from utils.constants import VISUAL_TYPES

# Configure matplotlib to use a non-interactive backend
matplotlib.use('Agg')

logger = logging.getLogger(__name__)

class VisualAgent(BaseAgent):
    """Agent responsible for generating visuals for content."""
    
    def __init__(self, gemini_client: Optional[GeminiClient] = None,
                 google_drive_client: Optional[GoogleDriveClient] = None,
                 stable_diffusion_client: Optional[StableDiffusionClient] = None,
                 huggingface_client: Optional[HuggingFaceClient] = None):
        super().__init__("Visual Agent", "Generates visual content for articles")
        self.gemini_client = gemini_client or GeminiClient()
        self.google_drive_client = google_drive_client or GoogleDriveClient()
        self.stable_diffusion_client = stable_diffusion_client or StableDiffusionClient()
        self.huggingface_client = huggingface_client or HuggingFaceClient()
        
        # Create output directory if it doesn't exist
        os.makedirs("data/visuals", exist_ok=True)
        
        # Define supported visual types and style presets
        self.supported_types = ["chart", "infographic", "quote_card", "diagram", "header_image"]
        self.style_presets = {
            "professional": {
                "color_scheme": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"],
                "font_family": "Arial",
                "background_color": "#FFFFFF",
                "text_color": "#333333",
                "accent_color": "#1f77b4"
            },
            "modern": {
                "color_scheme": ["#3498db", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c"],
                "font_family": "Helvetica",
                "background_color": "#FFFFFF",
                "text_color": "#2c3e50",
                "accent_color": "#3498db"
            },
            "minimal": {
                "color_scheme": ["#34495e", "#7f8c8d", "#95a5a6", "#bdc3c7", "#ecf0f1"],
                "font_family": "Calibri",
                "background_color": "#FFFFFF",
                "text_color": "#34495e",
                "accent_color": "#7f8c88d"
            }
        }
        
        # Determine which image generation client to use by default
        # Prioritize: 1. StableDiffusion, 2. HuggingFace, 3. Gemini placeholder
        if self.stable_diffusion_client.api_key:
            logger.info("Using Stable Diffusion API for image generation")
            self.default_image_client = "stable_diffusion"
        elif self.huggingface_client.api_token:
            logger.info("Using Hugging Face API for free image generation")
            self.default_image_client = "huggingface"
        else:
            logger.info("No image generation API keys found, will use placeholders")
            self.default_image_client = "placeholder"
        
    async def analyze_content(self, article: Article) -> Dict[str, Any]:
        """
        Analyze the article content to determine optimal visual strategy.
        
        Args:
            article: The article object containing content to analyze
            
        Returns:
            Dictionary with visual strategy details
        """
        try:
            logger.info(f"Analyzing content for visual strategy: {article.title}")
            
            # Extract key sections and information
            content = article.content
            if isinstance(content, str):
                try:
                    # Try to parse as JSON if it's a string that looks like JSON
                    if content.strip().startswith('{') and content.strip().endswith('}'):
                        content = json.loads(content)
                except:
                    # If parsing fails, keep it as a string
                    pass
            
            # If content is a dictionary, extract sections
            sections = []
            if isinstance(content, dict):
                # Extract introduction
                if "introduction" in content:
                    sections.append(("introduction", content["introduction"]))
                
                # Extract main content sections
                if "sections" in content and isinstance(content["sections"], list):
                    for i, section in enumerate(content["sections"]):
                        if isinstance(section, dict) and "heading" in section and "content" in section:
                            sections.append((section["heading"], section["content"]))
                
                # Extract conclusion
                if "conclusion" in content:
                    sections.append(("conclusion", content["conclusion"]))
            else:
                # For plain text content, try to extract sections based on headings
                text_sections = re.split(r'\n#{1,3}\s+', content)
                if len(text_sections) > 1:
                    # First item is before any heading, treat as intro
                    sections.append(("introduction", text_sections[0].strip()))
                    
                    # Extract headings
                    headings = re.findall(r'\n(#{1,3}\s+.+)', content)
                    
                    # Pair headings with content
                    for i in range(len(headings)):
                        if i + 1 < len(text_sections):
                            heading = headings[i].strip('#').strip()
                            sections.append((heading, text_sections[i+1].strip()))
            
            # Determine key themes, concepts, and data points
            themes_prompt = f"""
            Analyze the following article with title "{article.title}" and extract:
            1. The 3-5 main themes or key points
            2. Any data points, statistics, or numbers that could be visualized
            3. Any analogies, metaphors, or concepts that could be illustrated
            4. The emotional tone of the piece
            
            Article content:
            {article.content[:7000]}  # Limit content size to avoid token limits
            
            Respond in JSON format with these keys: themes, data_points, concepts, tone
            """
            
            themes_response = await self.gemini_client.generate_content(themes_prompt)
            
            try:
                visual_strategy = json.loads(themes_response)
            except:
                # If JSON parsing fails, create a basic strategy
                logger.warning("Couldn't parse visual strategy as JSON, creating basic strategy")
                visual_strategy = {
                    "themes": ["Article theme"],
                    "data_points": [],
                    "concepts": [],
                    "tone": "Informative"
                }
            
            # Determine optimal visual types and placement
            visual_plan = await self._create_visual_plan(article, sections, visual_strategy)
            
            return {
                "strategy": visual_strategy,
                "sections": sections,
                "visual_plan": visual_plan
            }
            
        except Exception as e:
            logger.error(f"Error analyzing content for visuals: {str(e)}")
            return {
                "strategy": {
                    "themes": [article.title],
                    "data_points": [],
                    "concepts": [],
                    "tone": "Informative"
                },
                "sections": [("article", article.content[:1000])],
                "visual_plan": {
                    "header_image": True,
                    "infographics": 0,
                    "charts": 0,
                    "quote_cards": 0
                }
            }
    
    async def _create_visual_plan(self, article: Article, sections: List[Tuple[str, str]], 
                                 strategy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a plan for what visuals to generate based on content analysis.
        
        Args:
            article: The article object
            sections: List of (heading, content) tuples
            strategy: The content analysis strategy
            
        Returns:
            Dictionary defining visual plan
        """
        # Basic plan
        plan = {
            "header_image": True,
            "infographics": 0,
            "charts": 0,
            "quote_cards": 0
        }
        
        # Determine if we need infographics
        if len(strategy.get("concepts", [])) > 0:
            plan["infographics"] = min(len(strategy.get("concepts", [])), 2)
            
        # Determine if we need charts
        if len(strategy.get("data_points", [])) > 0:
            plan["charts"] = min(len(strategy.get("data_points", [])), 2)
            
        # Determine if we need quote cards
        content_length = sum(len(content) for _, content in sections)
        if content_length > 2000 and len(sections) > 2:
            plan["quote_cards"] = 1
            
        # Adjust based on article length
        if content_length > 5000:
            plan["infographics"] = min(plan["infographics"] + 1, 3)
            plan["quote_cards"] = min(plan["quote_cards"] + 1, 2)
            
        logger.info(f"Visual plan created for {article.title}: {plan}")
        return plan
    
    async def generate_visuals(self, article: Article) -> List[Visual]:
        """
        Generate visuals for an article based on content analysis.
        
        Args:
            article: The article to generate visuals for
            
        Returns:
            List of Visual objects
        """
        visuals = []
        
        try:
            logger.info(f"Generating visuals for article: {article.title}")
            
            # Analyze content to determine optimal visual strategy
            analysis = await self.analyze_content(article)
            
            # Generate header image
            if analysis["visual_plan"]["header_image"]:
                header_image = await self._generate_header_image(article, analysis)
                if header_image:
                    visuals.append(header_image)
            
            # Generate infographics
            if analysis["visual_plan"]["infographics"] > 0:
                infographics = await self._generate_infographics(article, analysis)
                visuals.extend(infographics)
            
            # Generate charts
            if analysis["visual_plan"]["charts"] > 0:
                charts = await self._generate_charts(article, analysis)
                visuals.extend(charts)
            
            # Generate quote cards
            if analysis["visual_plan"]["quote_cards"] > 0:
                quote_cards = await self._generate_quote_cards(article, analysis)
                visuals.extend(quote_cards)
            
            logger.info(f"Generated {len(visuals)} visuals for article: {article.title}")
            return visuals
            
        except Exception as e:
            logger.error(f"Error generating visuals: {str(e)}")
            return []
    
    async def _generate_header_image(self, article: Article, analysis: Dict[str, Any]) -> Optional[Visual]:
        """
        Generate a header image for the article.
        
        Args:
            article: The article object
            analysis: The content analysis
            
        Returns:
            A Visual object or None if generation failed
        """
        try:
            logger.info(f"Generating header image for: {article.title}")
            
            # Create a prompt for the header image
            themes = analysis["strategy"].get("themes", [article.title])
            tone = analysis["strategy"].get("tone", "Informative")
            
            prompt = f"""
            Professional header image for an article titled: "{article.title}"
            
            Key themes: {', '.join(themes[:3])}
            Tone: {tone}
            
            High-quality, professional business image with modern design, clean layout.
            Suitable as a header at the top of a corporate article.
            No text overlay needed. Use relevant imagery representing {', '.join(themes[:2])}.
            """
            
            # Create a temporary Visual object for the generation process
            temp_visual = Visual(
                title=f"Header image for {article.title}",
                type="header_image",
                file_path=""
            )
            
            # Generate the image using Stable Diffusion
            image_path, metadata = await self._generate_image(prompt, temp_visual)
            
            if not image_path:
                logger.warning(f"Failed to generate header image for {article.title}")
                return None
                
            # Upload to Google Drive
            filename = f"header_{article.id}.png"
            with open(image_path, "rb") as f:
                image_data = f.read()
                
            file_id = await self.google_drive_client.upload_image(image_data, filename)
            
            # Clean up temporary file
            try:
                os.remove(image_path)
            except:
                pass
                
            if not file_id:
                logger.warning(f"Failed to upload header image for {article.title}")
                return None
                
            # Create the Visual object with only the fields supported by the model
            visual = Visual(
                title=f"Header image for {article.title}",
                type="header_image",
                file_path=file_id,
                article_id=article.id
            )
            
            logger.info(f"Successfully generated header image for {article.title}")
            return visual
            
        except Exception as e:
            logger.error(f"Error generating header image: {str(e)}")
            return None
    
    async def _generate_infographics(self, article: Article, analysis: Dict[str, Any]) -> List[Visual]:
        """
        Generate infographics based on key concepts from the article.
        
        Args:
            article: The article object
            analysis: The content analysis
            
        Returns:
            List of Visual objects
        """
        import tempfile
        infographics = []
        
        try:
            concepts = analysis["strategy"].get("concepts", [])
            if not concepts:
                return []
                
            # Limit to the number specified in the plan
            num_infographics = min(len(concepts), analysis["visual_plan"]["infographics"])
            
            for i in range(num_infographics):
                if i >= len(concepts):
                    break
                    
                concept = concepts[i]
                
                # Determine which section this infographic should be associated with
                relevant_section = None
                for heading, content in analysis["sections"]:
                    if isinstance(concept, str) and concept.lower() in content.lower():
                        relevant_section = heading
                        break
                
                if not relevant_section and analysis["sections"]:
                    # If no match found, place it in the first content section (not intro)
                    if len(analysis["sections"]) > 1:
                        relevant_section = analysis["sections"][1][0]
                    else:
                        relevant_section = analysis["sections"][0][0]
                
                prompt = f"""
                Create an informative infographic that explains this concept:
                "{concept}"
                
                This is for an article titled: "{article.title}"
                
                Professional business style infographic with clean design, clear organization.
                Use modern color scheme and simple icons to represent the concept.
                Include a clear title and concise text explaining the concept.
                """
                
                # Create a temporary Visual object for the generation process
                temp_visual = Visual(
                    title=f"Infographic: {str(concept)[:50]}..." if len(str(concept)) > 50 else f"Infographic: {concept}",
                    type="infographic",
                    file_path=""
                )
                
                # Generate the image using StableDiffusion if available
                image_path, metadata = await self._generate_image(prompt, temp_visual)
                
                if not image_path:
                    logger.warning(f"Failed to generate infographic for concept: {concept}")
                    continue
                    
                # Upload to Google Drive
                filename = f"infographic_{i}_{article.id}.png"
                
                with open(image_path, "rb") as f:
                    image_data = f.read()
                    
                file_id = await self.google_drive_client.upload_image(image_data, filename)
                
                # Clean up temporary file
                try:
                    os.remove(image_path)
                except:
                    pass
                    
                if not file_id:
                    logger.warning(f"Failed to upload infographic for concept: {concept}")
                    continue
                    
                # Create the Visual object
                visual = Visual(
                    title=f"Infographic: {str(concept)[:50]}..." if len(str(concept)) > 50 else f"Infographic: {concept}",
                    type="infographic",
                    file_path=file_id,
                    article_id=article.id
                )
                
                infographics.append(visual)
                logger.info(f"Generated infographic for concept: {concept}")
                
                # Add a small delay to avoid rate limiting
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error generating infographics: {str(e)}")
            
        return infographics
    
    async def _generate_charts(self, article: Article, analysis: Dict[str, Any]) -> List[Visual]:
        """
        Generate charts based on data points from the article.
        
        Args:
            article: The article object
            analysis: The content analysis
            
        Returns:
            List of Visual objects
        """
        import tempfile
        charts = []
        
        try:
            data_points = analysis["strategy"].get("data_points", [])
            if not data_points:
                return []
                
            # Limit to the number specified in the plan
            num_charts = min(len(data_points), analysis["visual_plan"]["charts"])
            
            for i in range(num_charts):
                if i >= len(data_points):
                    break
                    
                data_point = data_points[i]
                
                # Determine which section this chart should be associated with
                relevant_section = None
                for heading, content in analysis["sections"]:
                    if isinstance(data_point, str) and data_point.lower() in content.lower():
                        relevant_section = heading
                        break
                
                prompt = f"""
                Create a professional chart or data visualization for this data point:
                "{data_point}"
                
                This is for an article titled: "{article.title}"
                
                Make it a clean, clear chart with a professional design.
                Use appropriate chart type (bar, line, pie, etc.) for this data.
                Include a clear title and labels.
                """
                
                # Create a temporary Visual object for the generation process
                temp_visual = Visual(
                    title=f"Chart: {str(data_point)[:50]}..." if len(str(data_point)) > 50 else f"Chart: {data_point}",
                    type="chart",
                    file_path=""
                )
                
                # Generate the image using StableDiffusion if available
                image_path, metadata = await self._generate_image(prompt, temp_visual)
                
                if not image_path:
                    logger.warning(f"Failed to generate chart for data point: {data_point}")
                    continue
                    
                # Upload to Google Drive
                filename = f"chart_{i}_{article.id}.png"
                
                with open(image_path, "rb") as f:
                    image_data = f.read()
                    
                file_id = await self.google_drive_client.upload_image(image_data, filename)
                
                # Clean up temporary file
                try:
                    os.remove(image_path)
                except:
                    pass
                    
                if not file_id:
                    logger.warning(f"Failed to upload chart for data point: {data_point}")
                    continue
                    
                # Create the Visual object
                visual = Visual(
                    title=f"Chart: {str(data_point)[:50]}..." if len(str(data_point)) > 50 else f"Chart: {data_point}",
                    type="chart",
                    file_path=file_id,
                    article_id=article.id
                )
                
                charts.append(visual)
                logger.info(f"Generated chart for data point: {data_point}")
                
                # Add a small delay to avoid rate limiting
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error generating charts: {str(e)}")
            
        return charts
    
    async def _generate_quote_cards(self, article: Article, analysis: Dict[str, Any]) -> List[Visual]:
        """
        Generate quote cards for key quotes in the article.
        
        Args:
            article: The article object
            analysis: The content analysis
            
        Returns:
            List of Visual objects
        """
        import tempfile
        quote_cards = []
        
        try:
            # Extract quotes or key statements from the article content
            quotes = []
            
            # Try to find potential quotes
            for _, content in analysis["sections"]:
                # Look for quoted text
                quoted = re.findall(r'"([^"]+)"', content)
                quotes.extend(quoted)
                
                # Look for statements with strong claims or conclusive statements
                statements = re.findall(r'(?:In conclusion|To summarize|Finally|Importantly|Notably|Above all)[,:]?\s+([^\.]+\.)', content)
                quotes.extend(statements)
            
            # If we didn't find good quotes, generate some based on the themes
            if not quotes and analysis["strategy"].get("themes"):
                themes = analysis["strategy"].get("themes", [])
                for theme in themes[:analysis["visual_plan"]["quote_cards"]]:
                    if isinstance(theme, str):
                        prompt = f"""
                        Create a powerful, memorable quote that captures this key theme from the article:
                        "{theme}"
                        
                        The quote should be concise (under 20 words), impactful, and sound like it came from an expert.
                        Don't use quotation marks in your response, just the quote text.
                        """
                        
                        quote_response = await self.gemini_client.generate_content(prompt)
                        if quote_response:
                            quotes.append(quote_response.strip())
            
            # Limit to the number specified in the plan
            num_quote_cards = min(len(quotes), analysis["visual_plan"]["quote_cards"])
            
            for i in range(num_quote_cards):
                if i >= len(quotes):
                    break
                    
                quote = quotes[i]
                
                prompt = f"""
                Create a professional quote card with this quote: "{quote}"
                
                This is for an article titled: "{article.title}"
                
                High-quality business style quote card with elegant typography.
                The quote should be the focal point with elegant typography.
                Use a clean, professional background that evokes the theme of the article.
                Make the design modern and suitable for corporate/business context.
                """
                
                # Create a temporary Visual object for the generation process
                temp_visual = Visual(
                    title=f"Quote: {quote[:50]}..." if len(quote) > 50 else f"Quote: {quote}",
                    type="quote_card",
                    file_path=""
                )
                
                # Generate the image using StableDiffusion if available
                image_path, metadata = await self._generate_image(prompt, temp_visual)
                
                if not image_path:
                    logger.warning(f"Failed to generate quote card for: {quote[:30]}...")
                    continue
                    
                # Upload to Google Drive
                filename = f"quote_{i}_{article.id}.png"
                
                with open(image_path, "rb") as f:
                    image_data = f.read()
                    
                file_id = await self.google_drive_client.upload_image(image_data, filename)
                
                # Clean up temporary file
                try:
                    os.remove(image_path)
                except:
                    pass
                    
                if not file_id:
                    logger.warning(f"Failed to upload quote card for: {quote[:30]}...")
                    continue
                    
                # Create the Visual object
                visual = Visual(
                    title=f"Quote: {quote[:50]}..." if len(quote) > 50 else f"Quote: {quote}",
                    type="quote_card",
                    file_path=file_id,
                    article_id=article.id
                )
                
                quote_cards.append(visual)
                logger.info(f"Generated quote card for: {quote[:30]}...")
                
                # Add a small delay to avoid rate limiting
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error generating quote cards: {str(e)}")
            
        return quote_cards

    async def process(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Process the results of the visual generation and return analytics data."""
        logger.info("Processing visual generation results")
        return {
            "visual_count": len(results.get("visuals", [])),
            "visual_types": [v.type for v in results.get("visuals", [])],
            "processing_time": time.time()  # Simplified timing
        }

    async def run(self, article: Article, visual_types: List[str] = None) -> List[Visual]:
        """
        Main execution method for generating visuals for an article.
        
        Args:
            article: The article to generate visuals for
            visual_types: Optional list of specific visual types to generate
                        
        Returns:
            List of Visual objects created
        """
        logger.info(f"Starting visual generation for article: {article.title}")
        
        try:
            # Analyze the content to understand what visuals would be appropriate
            analysis = await self.analyze_content(article)
            
            # Generate the visuals based on the analysis
            visuals = []
            
            # Generate header image if needed
            if analysis["visual_plan"]["header_image"] and (not visual_types or "header_image" in visual_types):
                header_image = await self._generate_header_image(article, analysis)
                if header_image:
                    visuals.append(header_image)
            
            # Generate infographics if needed
            if analysis["visual_plan"]["infographics"] > 0 and (not visual_types or "infographic" in visual_types):
                infographics = await self._generate_infographics(article, analysis)
                visuals.extend(infographics)
            
            # Generate charts if needed
            if analysis["visual_plan"]["charts"] > 0 and (not visual_types or "chart" in visual_types):
                charts = await self._generate_charts(article, analysis)
                visuals.extend(charts)
            
            # Generate quote cards if needed
            if analysis["visual_plan"]["quote_cards"] > 0 and (not visual_types or "quote_card" in visual_types):
                quote_cards = await self._generate_quote_cards(article, analysis)
                visuals.extend(quote_cards)
            
            # Process results for metrics
            results = {
                "visuals": visuals,
                "analysis": analysis
            }
            metrics = await self.process(results)
            
            logger.info(f"Completed visual generation for article: {article.title}, created {len(visuals)} visuals")
            return visuals
            
        except Exception as e:
            logger.error(f"Error in visual generation: {str(e)}")
            return []

    async def analyze_content_for_visuals(self, article: Article) -> Dict[str, Any]:
        """
        Analyzes the article content to determine optimal visual placements.
        
        Args:
            article: The article content to analyze
            
        Returns:
            Dict with visual recommendations
        """
        logger.info(f"Analyzing content for visual opportunities in article: {article.title}")
        
        prompt = f"""
        Analyze the following article content and identify optimal opportunities for visuals.
        For each visual opportunity, provide:
        1. The type of visual that would be most effective (chart, infographic, quote card, etc.)
        2. A brief description of what the visual should contain
        3. The section where it should be placed
        4. Why this visual would enhance the content
        
        ARTICLE TITLE: {article.title}
        ARTICLE CONTENT:
        """
        
        # Add sections content
        for section in article.sections:
            prompt += f"\n\n## {section.title}\n{section.content}"
            
        prompt += """
        
        Respond in JSON format with an array of visual recommendations:
        {
          "visual_recommendations": [
            {
              "visual_type": "chart/infographic/quote_card/diagram/illustration",
              "title": "Brief title for the visual",
              "description": "Detailed description of what the visual should contain",
              "placement_section": "The section title where this should be placed",
              "rationale": "Why this visual enhances the content"
            }
          ]
        }
        """
        
        response = await self.gemini_client.generate_content(prompt)
        
        try:
            # Extract JSON from response
            json_str = response.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:-3]  # Remove ```json and ``` markers
            elif json_str.startswith("```"):
                json_str = json_str[3:-3]  # Remove ``` markers
                
            recommendations = json.loads(json_str)
            logger.info(f"Successfully analyzed content and found {len(recommendations.get('visual_recommendations', []))} visual opportunities")
            return recommendations
        except Exception as e:
            logger.error(f"Failed to parse visual recommendations: {e}")
            return {"visual_recommendations": []}
    
    async def generate_visuals(self, article: Article, visual_types: List[str] = None) -> List[Visual]:
        """
        Generates visual content based on article content.
        
        Args:
            article: The article to generate visuals for
            visual_types: List of visual types to generate (e.g., chart, infographic)
            
        Returns:
            List of Visual objects
        """
        if not visual_types:
            visual_types = [vt.value for vt in VisualType]
        
        logger.info(f"Generating visuals for article: {article.title}, types: {visual_types}")
        
        # Get recommendations for visual placements
        recommendations = await self.analyze_content_for_visuals(article)
        
        visuals = []
        for rec in recommendations.get("visual_recommendations", []):
            visual_type = rec.get("visual_type")
            
            # Skip if this visual type isn't requested
            if visual_type not in visual_types:
                continue
                
            # Map to a valid VisualType enum value if possible
            try:
                mapped_type = next((vt for vt in VisualType if vt.value == visual_type or vt.name.lower() == visual_type.lower()), None)
                if mapped_type:
                    visual_type = mapped_type
            except:
                # Keep original if mapping fails
                pass
            
            visual = Visual(
                type=visual_type,
                title=rec.get("title", "Untitled Visual"),
                description=rec.get("description", ""),
                best_placement=rec.get("placement_section")
            )
            
            visuals.append(visual)
            
        logger.info(f"Created {len(visuals)} visual specifications for article: {article.title}")
        return visuals
    
    async def generate_visual_prompts(self, visuals: List[Visual], article: Article) -> Dict[str, str]:
        """
        Generates specific prompts for each visual that can be used with image generation models.
        
        Args:
            visuals: List of Visual objects to generate prompts for
            article: The article context
            
        Returns:
            Dictionary mapping visual IDs to generation prompts
        """
        logger.info(f"Generating image prompts for {len(visuals)} visuals")
        
        prompts = {}
        for visual in visuals:
            prompt_template = f"""
            Create a detailed image generation prompt for a {visual.type} visualization based on this description:
            
            VISUAL TITLE: {visual.title}
            VISUAL DESCRIPTION: {visual.description}
            ARTICLE CONTEXT: {article.title}
            
            The image should be professional, high-quality, and suitable for business content.
            Format your response as a single detailed prompt that could be given directly to an image generation AI.
            """
            
            response = await self.gemini_client.generate_content(prompt_template)
            
            # Clean and format the response
            prompt = response.strip().replace('"', '')
            prompts[visual.id] = prompt
            
        logger.info(f"Successfully generated {len(prompts)} image prompts")
        return prompts
    
    def _get_section_by_title(self, article: Article, section_title: str) -> Optional[str]:
        """Helper to get a section content by its title."""
        for section in article.sections:
            if section.title.lower() == section_title.lower():
                return section.content
        return None
    
    async def _generate_image(self, prompt: str, visual: Visual) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Central method to generate an image using whatever client is available.
        Uses a priority system: 1. Stable Diffusion, 2. Hugging Face, 3. Mock images
        
        Args:
            prompt: The prompt to generate the image from
            visual: The Visual object containing metadata
            
        Returns:
            Tuple containing (temporary file path to the generated image, metadata)
        """
        logger.info(f"Generating image for visual: {visual.title}")
        
        # Try StableDiffusion first if API key is available
        if self.default_image_client == "stable_diffusion":
            try:
                logger.info("Using Stable Diffusion API for image generation")
                image_path, metadata = await self.stable_diffusion_client.generate_image(prompt, visual)
                if image_path:
                    logger.info(f"Successfully generated image with Stable Diffusion for: {visual.title}")
                    return image_path, metadata
            except Exception as e:
                logger.error(f"Error with Stable Diffusion image generation: {str(e)}")
        
        # Try Hugging Face if API token is available
        if self.default_image_client in ["huggingface", "placeholder"] and self.huggingface_client.api_token:
            try:
                logger.info("Using Hugging Face API for free image generation")
                image_path, metadata = await self.huggingface_client.generate_image(prompt, visual)
                if image_path:
                    logger.info(f"Successfully generated image with Hugging Face for: {visual.title}")
                    return image_path, metadata
            except Exception as e:
                logger.error(f"Error with Hugging Face image generation: {str(e)}")
        
        # Try mock generation with Hugging Face 
        try:
            logger.info("Using Hugging Face mock image generation")
            image_path, metadata = await self.huggingface_client.generate_image_mock(prompt, visual)
            if image_path:
                logger.info(f"Successfully generated mock image with Hugging Face for: {visual.title}")
                return image_path, metadata
        except Exception as e:
            logger.error(f"Error with Hugging Face mock generation: {str(e)}")
        
        # Last resort: Stable Diffusion mock image
        try:
            logger.info("Using Stable Diffusion mock image generation")
            image_path, metadata = await self.stable_diffusion_client.generate_image_mock(prompt, visual)
            if image_path:
                logger.info(f"Successfully generated mock image with Stable Diffusion for: {visual.title}")
                return image_path, metadata
        except Exception as e:
            logger.error(f"Error with Stable Diffusion mock generation: {str(e)}")
        
        # Absolute last resort: Gemini placeholder
        try:
            logger.info("Using Gemini placeholder as last resort")
            image_data = await self.gemini_client.generate_image(prompt)
            if image_data:
                # Save to a temporary file
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                    temp_file.write(image_data)
                    image_path = temp_file.name
                
                logger.info(f"Successfully generated Gemini placeholder for: {visual.title}")
                return image_path, {"mock": True, "source": "gemini_placeholder"}
        except Exception as e:
            logger.error(f"Error with Gemini placeholder generation: {str(e)}")
        
        logger.error(f"All image generation methods failed for visual: {visual.title}")
        return None, None
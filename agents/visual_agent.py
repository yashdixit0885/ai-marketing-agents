import os
import json
from io import BytesIO
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .base_agent import BaseAgent
from services.api_clients.gemini_client import GeminiClient
from models.content_models import Visual, Article
from models import db_session

class VisualAgent(BaseAgent):
    """Agent responsible for creating visual content."""
    
    def __init__(self):
        super().__init__("Visual Agent", "Creates visual content to accompany articles")
        self.gemini_client = GeminiClient()
        
        # Create output directory if it doesn't exist
        os.makedirs("data/visuals", exist_ok=True)
    
    # agents/visual_agent.py (update the run method)
    async def run(self, article_id, visual_type="chart"):
        """Generate visual content for an article."""
        self.log_status(f"Starting visual generation for article: {article_id}")
        
        # Retrieve the article
        article = db_session.get(Article, article_id)
        if not article:
            raise ValueError(f"Article with ID {article_id} not found")
        
        # Generate visual based on type
        if visual_type == "chart":
            visual_data = await self._generate_chart(article)
        elif visual_type == "infographic":
            visual_data = await self._generate_infographic(article)
        elif visual_type == "quote_card":
            visual_data = await self._generate_quote_card(article)
        else:
            visual_data = await self._generate_basic_visual(article)
        
        # Process and store the visual
        visual = await self.process({
            "article": article,
            "visual_data": visual_data,
            "type": visual_type
        })
        
        self.log_status(f"Completed visual generation: {visual.title}")
        return visual
    
    async def _generate_chart(self, article):
        """Generate a chart based on the article content."""
        # Extract key data points from the article
        prompt = f"""
        Extract key numerical data points from the following article that could be presented in a chart:
        {article.content[:2000]}  # Limit content to avoid token limits
        
        Return the data in JSON format with:
        1. chart_type: The recommended chart type (bar, line, pie)
        2. title: A short descriptive title
        3. data: The data points in an appropriate format
        4. labels: Labels for the data points
        5. x_axis: Label for x-axis (if applicable)
        6. y_axis: Label for y-axis (if applicable)
        
        Make sure the data is properly structured for the chart type.
        """
        
        response = await self.gemini_client.generate_content(prompt)
        try:
            chart_data = json.loads(response)
        except json.JSONDecodeError:
            # If parsing fails, create a simple fallback chart
            chart_data = {
                "chart_type": "bar",
                "title": f"Key Metrics for {article.title[:30]}",
                "data": [5, 7, 9, 8, 6],
                "labels": ["Metric A", "Metric B", "Metric C", "Metric D", "Metric E"],
                "x_axis": "Metrics",
                "y_axis": "Value"
            }
        
        # Generate the chart
        plt.figure(figsize=(10, 6))
        
        if chart_data["chart_type"] == "bar":
            plt.bar(chart_data["labels"], chart_data["data"])
        elif chart_data["chart_type"] == "line":
            plt.plot(chart_data["labels"], chart_data["data"])
        elif chart_data["chart_type"] == "pie":
            plt.pie(chart_data["data"], labels=chart_data["labels"], autopct='%1.1f%%')
        
        plt.title(chart_data["title"])
        if chart_data.get("x_axis"):
            plt.xlabel(chart_data["x_axis"])
        if chart_data.get("y_axis"):
            plt.ylabel(chart_data["y_axis"])
        
        plt.tight_layout()
        
        # Save chart to a file
        filename = f"data/visuals/chart_{article.id}_{int(os.urandom(2).hex(), 16)}.png"
        plt.savefig(filename)
        plt.close()
        
        return {
            "title": chart_data["title"],
            "filename": filename,
            "chart_data": chart_data
        }
    
    async def _generate_quote_card(self, article):
        """Generate a quote card based on the article."""
        # Extract a quote from the article
        prompt = f"""
        Extract an impactful quote or key takeaway from the following article:
        {article.content[:2000]}  # Limit content to avoid token limits
        
        Return the quote (max 20 words) and a brief attribution if applicable.
        Make sure the quote is impactful and relevant to the main message of the article.
        """
        
        response = await self.gemini_client.generate_content(prompt)
        quote = response.strip()
        
        # Create a simple quote card
        img = Image.new('RGB', (800, 400), color=(53, 59, 72))
        d = ImageDraw.Draw(img)
        
        # Try to load a font, use default if not available
        try:
            font_large = ImageFont.truetype("Arial", 32)
            font_small = ImageFont.truetype("Arial", 20)
        except IOError:
            font_large = ImageFont.load_default()
            font_small = font_large
        
        # Add quote
        d.text((40, 100), f'"{quote}"', fill=(236, 240, 241), font=font_large)
        
        # Add attribution and branding
        d.text((40, 320), f"From: {article.title[:50]}", fill=(236, 240, 241), font=font_small)
        d.text((600, 360), "AI Content Automation", fill=(236, 240, 241), font=font_small)
        
        # Save quote card to a file
        filename = f"data/visuals/quote_{article.id}_{int(os.urandom(2).hex(), 16)}.png"
        img.save(filename)
        
        return {
            "title": f"Quote from {article.title[:30]}",
            "filename": filename,
            "quote": quote
        }
    
    async def _generate_infographic(self, article):
        """Generate a simple infographic based on the article."""
        # For now, create a placeholder infographic
        # In a real implementation, you would use a more sophisticated approach
        
        # Create a simple infographic template
        img = Image.new('RGB', (800, 1200), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        
        # Try to load a font, use default if not available
        try:
            title_font = ImageFont.truetype("Arial", 40)
            header_font = ImageFont.truetype("Arial", 30)
            body_font = ImageFont.truetype("Arial", 20)
        except IOError:
            title_font = ImageFont.load_default()
            header_font = title_font
            body_font = title_font
        
        # Add title
        d.rectangle([(0, 0), (800, 100)], fill=(41, 128, 185))
        d.text((40, 30), article.title[:50], fill=(255, 255, 255), font=title_font)
        
        # Extract key points for the infographic
        prompt = f"""
        Extract 3-5 key points from this article that would work well in an infographic:
        {article.content[:2000]}
        
        Format each point as a short headline (max 8 words) followed by a brief explanation (max 20 words).
        Return in JSON format with an array of objects containing 'headline' and 'description'.
        """
        
        response = await self.gemini_client.generate_content(prompt)
        try:
            points = json.loads(response)
        except json.JSONDecodeError:
            # Fallback points if parsing fails
            points = {
                "points": [
                    {"headline": "Key Point 1", "description": "Brief explanation of point 1"},
                    {"headline": "Key Point 2", "description": "Brief explanation of point 2"},
                    {"headline": "Key Point 3", "description": "Brief explanation of point 3"}
                ]
            }
        
        # Add points to infographic
        y_position = 150
        colors = [(231, 76, 60), (46, 204, 113), (155, 89, 182), (52, 152, 219), (241, 196, 15)]
        
        for i, point in enumerate(points.get("points", [])[:5]):
            # Add colored box for the point
            box_color = colors[i % len(colors)]
            d.rectangle([(40, y_position), (760, y_position + 180)], fill=(245, 245, 245), outline=box_color, width=3)
            
            # Add headline
            d.rectangle([(40, y_position), (760, y_position + 50)], fill=box_color)
            d.text((50, y_position + 10), point.get("headline", f"Point {i+1}"), fill=(255, 255, 255), font=header_font)
            
            # Add description
            d.text((50, y_position + 70), point.get("description", "Description text here"), fill=(0, 0, 0), font=body_font)
            
            y_position += 200
        
        # Add footer
        d.rectangle([(0, 1100), (800, 1200)], fill=(41, 128, 185))
        d.text((300, 1140), "AI Content Automation", fill=(255, 255, 255), font=header_font)
        
        # Save infographic to a file
        filename = f"data/visuals/infographic_{article.id}_{int(os.urandom(2).hex(), 16)}.png"
        img.save(filename)
        
        return {
            "title": f"Infographic: {article.title[:30]}",
            "filename": filename
        }
    
    async def _generate_basic_visual(self, article):
        """Generate a basic visual for the article."""
        # Create a simple colored rectangle with the article title
        img = Image.new('RGB', (800, 400), color=(41, 128, 185))
        d = ImageDraw.Draw(img)
        
        # Try to load a font, use default if not available
        try:
            font = ImageFont.truetype("Arial", 40)
            small_font = ImageFont.truetype("Arial", 20)
        except IOError:
            font = ImageFont.load_default()
            small_font = font
        
        # Add title text
        title = article.title[:60] + "..." if len(article.title) > 60 else article.title
        d.text((50, 150), title, fill=(255, 255, 255), font=font)
        d.text((50, 300), "AI Content Automation", fill=(255, 255, 255), font=small_font)
        
        # Save visual to file
        filename = f"data/visuals/basic_{article.id}_{int(os.urandom(2).hex(), 16)}.png"
        img.save(filename)
        
        return {
            "title": f"Visual for: {article.title[:30]}",
            "filename": filename
        }
    
    async def process(self, data):
        """Process and store the visual."""
        article = data["article"]
        visual_data = data["visual_data"]
        visual_type = data["type"]
        
        # Create the visual record
        visual = Visual(
            type=visual_type,
            title=visual_data["title"],
            file_path=visual_data["filename"],
            article_id=article.id
        )
        
        db_session.add(visual)
        db_session.commit()
        
        return visual
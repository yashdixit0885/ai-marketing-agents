import os
import io
import logging
import base64
import aiohttp
import tempfile
from typing import Dict, Any, Optional, Tuple, List
from PIL import Image, ImageDraw, ImageFont
from models.content_models import Visual

logger = logging.getLogger(__name__)

class HuggingFaceClient:
    """Client for interacting with Hugging Face Inference API for free image generation."""
    
    def __init__(self):
        # Hugging Face API token - you can get a free one at https://huggingface.co/settings/tokens
        self.api_token = os.getenv("HUGGINGFACE_API_TOKEN", "")
        
        # Default model for image generation (Stable Diffusion v2 by default)
        self.model_id = os.getenv("HUGGINGFACE_MODEL_ID", "stabilityai/stable-diffusion-2")
        
        # API endpoint based on the model
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model_id}"
        
        # Headers for authentication
        self.headers = {
            "Authorization": f"Bearer {self.api_token}"
        }
    
    async def generate_image(self, prompt: str, visual: Visual) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Generates an image using Hugging Face Inference API based on the provided prompt.
        
        Args:
            prompt: Text prompt for image generation
            visual: Visual object with metadata
            
        Returns:
            Tuple containing (temporary file path to the generated image, metadata)
        """
        logger.info(f"Generating image through Hugging Face for visual: {visual.title}")
        
        # Default parameters for the request
        payload = {
            "inputs": prompt,
            "parameters": {
                "negative_prompt": "blurry, bad quality, disfigured, ugly",
                "guidance_scale": 7.5,
                "num_inference_steps": 25
            }
        }
        
        # Adjust parameters based on visual type
        visual_type = str(visual.type).lower()
        if "chart" in visual_type or "graph" in visual_type:
            payload["parameters"]["negative_prompt"] += ", abstract, photographic, realistic"
        elif "infographic" in visual_type:
            payload["parameters"]["negative_prompt"] += ", abstract, photographic"
        elif "quote" in visual_type:
            payload["parameters"]["negative_prompt"] += ", messy, cluttered"
        
        try:
            # Check if API token is available
            if not self.api_token:
                logger.warning("No Hugging Face API token provided. Using fallback to mock image.")
                return await self.generate_image_mock(prompt, visual)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url, 
                    headers=self.headers,
                    json=payload
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error generating image: {response.status}, {error_text}")
                        logger.warning("Using fallback to mock image due to API error")
                        return await self.generate_image_mock(prompt, visual)
                    
                    # Get the binary image data
                    image_data = await response.read()
                    
                    # Create a temporary file to store the image
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                        temp_file.write(image_data)
                        temp_path = temp_file.name
                    
                    logger.info(f"Successfully generated image for visual: {visual.title}")
                    
                    # Return the path to the temporary file and metadata
                    metadata = {
                        "model": self.model_id,
                        "prompt": prompt,
                        "source": "huggingface"
                    }
                    
                    return temp_path, metadata
                        
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            logger.warning("Using fallback to mock image due to exception")
            return await self.generate_image_mock(prompt, visual)
    
    async def generate_image_mock(self, prompt: str, visual: Visual) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Mock implementation for image generation. Creates a simple styled image with the prompt text.
        Used when the API token is not available or when the API call fails.
        
        Args:
            prompt: Text prompt for image generation
            visual: Visual object with metadata
            
        Returns:
            Tuple containing (temporary file path to the generated image, metadata)
        """
        logger.info(f"Generating mock image for visual: {visual.title}")
        
        try:
            # Default dimensions
            width, height = 1024, 1024
            
            # Adjust dimensions based on visual type
            visual_type = str(visual.type).lower()
            if "quote" in visual_type:
                width, height = 1080, 1080
            elif "header_image" in visual_type:
                width, height = 1200, 628  # 1.91:1 aspect ratio for headers
            
            # Create a gradient background
            image = Image.new('RGB', (width, height))
            draw = ImageDraw.Draw(image)
            
            # Different background styles based on visual type
            if "chart" in visual_type:
                # Blue gradient for charts
                for y in range(height):
                    r = int(50 + (y / height) * 100)
                    g = int(100 + (y / height) * 100)
                    b = int(150 + (y / height) * 50)
                    for x in range(width):
                        draw.point((x, y), fill=(r, g, b))
            elif "quote" in visual_type:
                # Purple gradient for quotes
                for y in range(height):
                    r = int(100 + (y / height) * 50)
                    g = int(50 + (y / height) * 50)
                    b = int(150 + (y / height) * 100)
                    for x in range(width):
                        draw.point((x, y), fill=(r, g, b))
            else:
                # Default gradient
                for y in range(height):
                    r = int(100 + (y / height) * 100)
                    g = int(100 + (y / height) * 100)
                    b = int(120 + (y / height) * 100)
                    for x in range(width):
                        draw.point((x, y), fill=(r, g, b))
            
            # Add visual type label
            try:
                font_path = "/System/Library/Fonts/Helvetica.ttc"
                font = ImageFont.truetype(font_path, 32)
                type_label = f"{visual.type.upper()}"
                draw.text((20, 20), type_label, fill=(255, 255, 255), font=font)
            except Exception:
                # Fallback if font loading fails
                draw.text((20, 20), f"{visual.type.upper()}", fill=(255, 255, 255))
            
            # Add a shortened prompt as text
            short_prompt = prompt[:100] + "..." if len(prompt) > 100 else prompt
            
            try:
                title_font = ImageFont.truetype(font_path, 24)
                # Wrap text to fit width
                text_lines = []
                words = short_prompt.split()
                current_line = ""
                for word in words:
                    test_line = current_line + " " + word if current_line else word
                    # Check if adding this word exceeds width
                    if title_font.getlength(test_line) < width - 100:
                        current_line = test_line
                    else:
                        text_lines.append(current_line)
                        current_line = word
                
                if current_line:
                    text_lines.append(current_line)
                
                # Draw each line
                for i, line in enumerate(text_lines):
                    y_position = height // 2 - len(text_lines) * 15 + i * 30
                    draw.text((width//2-title_font.getlength(line)//2, y_position), line, fill=(255, 255, 255), font=title_font)
            except Exception as e:
                # Fallback if sophisticated text rendering fails
                draw.text((width//4, height//2), short_prompt, fill=(255, 255, 255))
            
            # Add a watermark
            draw.text((width-180, height-30), "Hugging Face Mock", fill=(200, 200, 200))
            
            # Save the image to a temporary file
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                image.save(temp_file, format="PNG")
                temp_path = temp_file.name
            
            metadata = {
                "width": width,
                "height": height,
                "prompt": prompt,
                "mock": True
            }
            
            logger.info(f"Successfully generated mock image for visual: {visual.title}")
            return temp_path, metadata
            
        except Exception as e:
            logger.error(f"Error generating mock image: {str(e)}")
            return None, None
            
    async def list_available_models(self) -> List[Dict[str, Any]]:
        """
        Lists available image generation models on Hugging Face Hub.
        
        Returns:
            List of model information dictionaries
        """
        try:
            if not self.api_token:
                logger.error("No Hugging Face API token provided for listing models")
                return []
                
            api_url = "https://huggingface.co/api/models"
            params = {
                "filter": "image-to-image,text-to-image",
                "sort": "downloads",
                "direction": -1,
                "limit": 20
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    api_url,
                    headers=self.headers,
                    params=params
                ) as response:
                    if response.status != 200:
                        logger.error(f"Error listing models: {response.status}")
                        return []
                        
                    result = await response.json()
                    logger.info(f"Successfully retrieved {len(result)} Hugging Face image models")
                    return result
                    
        except Exception as e:
            logger.error(f"Error listing Hugging Face models: {str(e)}")
            return []
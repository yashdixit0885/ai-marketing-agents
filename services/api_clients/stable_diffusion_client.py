import os
import io
import logging
import base64
import aiohttp
import tempfile
from typing import Dict, Any, Optional, Tuple
from PIL import Image
from models.content_models import Visual

logger = logging.getLogger(__name__)

class StableDiffusionClient:
    """Client for interacting with Stable Diffusion API for image generation."""
    
    def __init__(self):
        self.api_key = os.getenv("STABILITY_API_KEY")
        self.api_url = os.getenv("STABILITY_API_URL", "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image")
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    async def generate_image(self, prompt: str, visual: Visual) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Generates an image using Stable Diffusion based on the provided prompt.
        
        Args:
            prompt: Text prompt for image generation
            visual: Visual object with metadata
            
        Returns:
            Tuple containing (temporary file path to the generated image, metadata)
        """
        if not self.api_key:
            logger.error("Stability API key not set in environment variables")
            return None, None
            
        logger.info(f"Generating image for visual: {visual.title}")
        
        # Default parameters for image generation
        params = {
            "text_prompts": [
                {
                    "text": prompt,
                    "weight": 1.0
                }
            ],
            "cfg_scale": 7,
            "steps": 30,
            "width": 1024,
            "height": 1024,
            "samples": 1,
            "style_preset": "photographic"
        }
        
        # Adjust parameters based on visual type
        visual_type = str(visual.type).lower()
        if "chart" in visual_type or "graph" in visual_type:
            params["style_preset"] = "digital-art"
        elif "infographic" in visual_type:
            params["style_preset"] = "digital-art"
        elif "quote" in visual_type:
            params["style_preset"] = "photographic"
            # Optimize dimensions for quote cards
            params["width"] = 1080
            params["height"] = 1080
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url, 
                    headers=self.headers,
                    json=params
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error generating image: {response.status}, {error_text}")
                        return None, None
                    
                    result = await response.json()
                    
                    # Process and save the image to a temporary file
                    if "artifacts" in result and len(result["artifacts"]) > 0:
                        image_data = base64.b64decode(result["artifacts"][0]["base64"])
                        
                        # Create a temporary file to store the image
                        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                            temp_file.write(image_data)
                            temp_path = temp_file.name
                        
                        logger.info(f"Successfully generated image for visual: {visual.title}")
                        
                        # Return the path to the temporary file and metadata
                        metadata = {
                            "seed": result["artifacts"][0].get("seed"),
                            "width": params["width"],
                            "height": params["height"],
                            "style_preset": params["style_preset"],
                            "prompt": prompt
                        }
                        
                        return temp_path, metadata
                    else:
                        logger.error("No artifacts found in the generation result")
                        return None, None
                        
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            return None, None
    
    async def generate_image_mock(self, prompt: str, visual: Visual) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Mock implementation for image generation. Creates a simple colored image with text.
        Useful for testing when API access is not available.
        
        Args:
            prompt: Text prompt for image generation
            visual: Visual object with metadata
            
        Returns:
            Tuple containing (temporary file path to the generated image, metadata)
        """
        logger.info(f"Generating mock image for visual: {visual.title}")
        
        try:
            # Create a simple colored image with the title text
            width, height = 1024, 1024
            image = Image.new('RGB', (width, height), color=(240, 240, 240))
            
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
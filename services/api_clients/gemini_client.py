import google.generativeai as genai
from config.settings import settings
import logging
import os
import base64
import io
from PIL import Image

logger = logging.getLogger(__name__)

class GeminiClient:
    """Client for interacting with Google's Gemini API."""
    
    def __init__(self):
        self.api_key = settings.GOOGLE_API_KEY
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        self.image_model = genai.GenerativeModel('gemini-pro-vision')
    
    async def generate_content(self, prompt):
        """Generate content using Gemini."""
        response = self.model.generate_content(prompt)
        return response.text
        
    async def generate_image(self, prompt):
        """
        Generate an image based on the prompt.
        This creates a simple placeholder image with text since Gemini doesn't generate images directly.
        In a production environment, this would use actual image generation APIs like Dall-E or Stable Diffusion.
        
        Args:
            prompt: Description of the image to generate
            
        Returns:
            Image data as bytes
        """
        try:
            logger.info(f"Generating image for prompt: {prompt[:50]}...")
            
            # Create a simple image with the prompt text
            # This is a placeholder - in production, connect to a real image generation API
            width, height = 800, 450
            
            # Create a blank image with a white background
            from PIL import Image, ImageDraw, ImageFont
            image = Image.new('RGB', (width, height), color=(255, 255, 255))
            draw = ImageDraw.Draw(image)
            
            # Draw a colored background
            draw.rectangle([(0, 0), (width, height)], fill=(240, 248, 255))
            
            # Add a border
            border_width = 10
            draw.rectangle([(0, 0), (width, height)], outline=(70, 130, 180), width=border_width)
            
            # Draw placeholder text
            try:
                font = ImageFont.truetype("Arial", 20)
            except IOError:
                font = ImageFont.load_default()
            
            # Use the first 100 chars of prompt as text in the image
            display_text = f"Image Placeholder: {prompt[:100]}..." if len(prompt) > 100 else f"Image Placeholder: {prompt}"
            
            # Word wrap the text to fit the image width
            lines = []
            words = display_text.split()
            current_line = ""
            
            for word in words:
                test_line = current_line + word + " "
                text_width = draw.textlength(test_line, font=font)
                
                if text_width < width - 60:  # Leave margins
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word + " "
                    
            lines.append(current_line)  # Add the last line
            
            # Calculate text height for centering
            line_height = font.getsize("A")[1] + 5
            text_height = len(lines) * line_height
            y_position = (height - text_height) // 2
            
            # Draw each line of text
            for line in lines:
                text_width = draw.textlength(line, font=font)
                position = ((width - text_width) // 2, y_position)
                draw.text(position, line, font=font, fill=(0, 0, 0))
                y_position += line_height
            
            # Save to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            # Ensure the directory exists
            os.makedirs("data/visuals", exist_ok=True)
            
            # Also save to disk for debugging purposes
            import random
            random_id = random.randint(1000, 99999)
            filepath = f"data/visuals/placeholder_{random_id}.png"
            image.save(filepath)
            
            logger.info(f"Generated placeholder image saved to {filepath}")
            
            return img_byte_arr.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            return None
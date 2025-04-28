import google.generativeai as genai
from config.settings import settings

class GeminiClient:
    """Client for interacting with Google's Gemini API."""
    
    def __init__(self):
        self.api_key = settings.GOOGLE_API_KEY
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
    
    async def generate_content(self, prompt):
        """Generate content using Gemini."""
        response = self.model.generate_content(prompt)
        return response.text
import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()

# Configure the API key
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Test the connection
model = genai.GenerativeModel('gemini-1.5-pro')
response = model.generate_content("Hello, Gemini!")
print(response.text)
import re
import json
import datetime
from typing import Any, Dict, List, Optional

def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    # Remove special characters
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text.lower())
    
    # Replace spaces with hyphens
    text = re.sub(r'\s+', '-', text)
    
    # Remove consecutive hyphens
    text = re.sub(r'-+', '-', text)
    
    # Trim hyphens from start and end
    text = text.strip('-')
    
    return text

def clean_text(text: str) -> str:
    """Clean text for use in APIs and documents."""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove trailing/leading whitespace
    text = text.strip()
    
    # Replace problematic characters
    text = text.replace('\0', '')
    
    # Normalize newlines to single \n
    text = re.sub(r'\r\n|\r', '\n', text)
    
    # Remove excessive newlines (more than 2 in a row)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text

def format_datetime(dt: datetime.datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format a datetime object to a string."""
    return dt.strftime(format_str)

def parse_datetime(dt_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime.datetime:
    """Parse a string to a datetime object."""
    return datetime.datetime.strptime(dt_str, format_str)

def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """Safely parse JSON string."""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return default

def truncate_text(text: str, max_length: int = 100, add_ellipsis: bool = True) -> str:
    """Truncate text to the specified maximum length."""
    if len(text) <= max_length:
        return text
    
    truncated = text[:max_length].rsplit(' ', 1)[0]
    if add_ellipsis:
        truncated += "..."
    
    return truncated

def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """Extract keywords from text."""
    # This is a simple implementation that could be enhanced with NLP libraries
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with",
                 "by", "about", "as", "of", "like", "this", "that", "these", "those"}
    
    # Extract words and convert to lowercase
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Remove stop words and count word frequency
    word_counts = {}
    for word in words:
        if word not in stop_words:
            word_counts[word] = word_counts.get(word, 0) + 1
    
    # Get the most frequent words
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in sorted_words[:max_keywords]]

def generate_filename(base_name: str, extension: str = 'txt') -> str:
    """Generate a filename with timestamp."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = slugify(base_name)
    return f"{slug}_{timestamp}.{extension}"
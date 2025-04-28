import re
from typing import List, Dict, Any

def extract_key_sentences(text: str, count: int = 5) -> List[str]:
    """Extract key sentences from text based on simple heuristics."""
    # Split text into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Score sentences based on simple heuristics
    scored_sentences = []
    for sentence in sentences:
        # Skip very short sentences
        if len(sentence.split()) < 5:
            continue
            
        # Calculate a simple score based on length and presence of keywords
        score = len(sentence.split()) * 0.1  # Longer sentences get higher score
        
        # Keywords that indicate importance
        keywords = ["important", "significant", "key", "crucial", "essential", 
                   "major", "primary", "critical", "vital", "conclusion"]
        
        for keyword in keywords:
            if keyword.lower() in sentence.lower():
                score += 1
        
        # Bonus for sentences containing numbers (often facts/statistics)
        if re.search(r'\d+', sentence):
            score += 0.5
            
        scored_sentences.append((sentence, score))
    
    # Sort by score and take the top 'count' sentences
    sorted_sentences = sorted(scored_sentences, key=lambda x: x[1], reverse=True)
    top_sentences = [s[0] for s in sorted_sentences[:count]]
    
    return top_sentences

def extract_stats_and_figures(text: str) -> List[str]:
    """Extract statistics and numerical figures from text."""
    # Find sentences containing numbers
    sentences = re.split(r'(?<=[.!?])\s+', text)
    stats = [s for s in sentences if re.search(r'\d+', s)]
    
    return stats

def generate_hashtags(text: str, count: int = 5) -> List[str]:
    """Generate relevant hashtags from text."""
    # Common words to exclude
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with",
                 "by", "about", "as", "of", "like", "this", "that", "these", "those", "is", 
                 "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", 
                 "does", "did", "can", "could", "will", "would", "should", "shall"}
    
    # Extract words, remove punctuation, and convert to lowercase
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    
    # Remove stop words and count word frequency
    word_counts = {}
    for word in words:
        if word not in stop_words:
            word_counts[word] = word_counts.get(word, 0) + 1
    
    # Get the most frequent words
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    top_words = [word for word, _ in sorted_words[:count]]
    
    # Convert to hashtags
    hashtags = ["#" + word for word in top_words]
    
    return hashtags

def summarize_text(text: str, max_words: int = 100) -> str:
    """Create a simple summary of text."""
    # Get key sentences
    key_sentences = extract_key_sentences(text, count=3)
    
    # Combine into a summary
    summary = " ".join(key_sentences)
    
    # Truncate if necessary
    words = summary.split()
    if len(words) > max_words:
        summary = " ".join(words[:max_words]) + "..."
    
    return summary
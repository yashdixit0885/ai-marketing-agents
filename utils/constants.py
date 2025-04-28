"""Constants used throughout the application."""

# Publication platforms
PLATFORMS = {
    "linkedin": "LinkedIn",
    "twitter": "Twitter",
    "medium": "Medium",
    "substack": "Substack"
}

# Content types
CONTENT_TYPES = {
    "article": "Article",
    "social_post": "Social Post",
    "visual": "Visual"
}

# Article statuses
ARTICLE_STATUSES = {
    "draft": "Draft",
    "review": "In Review",
    "published": "Published"
}

# Social post statuses
POST_STATUSES = {
    "draft": "Draft",
    "scheduled": "Scheduled",
    "published": "Published"
}

# Visual types
VISUAL_TYPES = {
    "chart": "Chart",
    "infographic": "Infographic",
    "quote_card": "Quote Card",
    "other": "Other"
}

# Default content schedule (days of week, 0 = Monday)
DEFAULT_SCHEDULE = {
    "research_days": [0, 4],  # Monday and Friday
    "writing_days": [1, 5],   # Tuesday and Saturday
    "publishing_days": [2, 6]  # Wednesday and Sunday
}

# Default topics for content
DEFAULT_TOPICS = [
    "AI and Business Automation",
    "Machine Learning for Decision Making",
    "Natural Language Processing Applications",
    "Computer Vision in Industry",
    "Ethical AI Implementation",
    "AI and ROI Considerations",
    "Future of AI in Business",
    "AI Integration Strategies",
    "AI Case Studies",
    "Emerging AI Technologies"
]
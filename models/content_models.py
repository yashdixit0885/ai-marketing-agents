from sqlalchemy import Column, String, Text, Integer, ForeignKey, Enum, Boolean, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel

class ResearchItem(BaseModel):
    __tablename__ = "research_items"
    
    title = Column(String(255), nullable=False)
    source = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=True)
    
    # Relationships
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=True)
    article = relationship("Article", back_populates="research_items")

class Article(BaseModel):
    __tablename__ = "articles"
    
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(Enum("draft", "review", "published", name="article_status"), default="draft")
    word_count = Column(Integer, nullable=True)
    
    # Relationships
    research_items = relationship("ResearchItem", back_populates="article")
    social_posts = relationship("SocialPost", back_populates="article")
    visuals = relationship("Visual", back_populates="article")

class SocialPost(BaseModel):
    __tablename__ = "social_posts"
    
    platform = Column(Enum("linkedin", "twitter", "medium", "substack", name="platform_type"))
    content = Column(Text, nullable=False)
    status = Column(Enum("draft", "scheduled", "published", name="post_status"), default="draft")
    scheduled_time = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    article = relationship("Article", back_populates="social_posts")

class Visual(BaseModel):
    __tablename__ = "visuals"
    
    type = Column(Enum("chart", "infographic", "quote_card", "other", name="visual_type"))
    title = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=False)
    
    # Relationships
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    article = relationship("Article", back_populates="visuals")
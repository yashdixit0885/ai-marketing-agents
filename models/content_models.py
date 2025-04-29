# models/content_models.py

from sqlalchemy import Column, String, Text, Integer, ForeignKey, Enum, Boolean, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel

class ResearchItem(BaseModel):
    __tablename__ = "research_items"
    
    title = Column(String(255), nullable=False)
    source = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    meta_data = Column(JSON, nullable=True)
    
    # Relationships
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=True)
    article = relationship("Article", back_populates="research_items")

class Article(BaseModel):
    __tablename__ = "articles"
    
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(Enum("draft", "review", "published", name="article_status"), default="draft")
    word_count = Column(Integer, nullable=True)
    
    # Add new review fields
    review_status = Column(Enum("pending", "approved", "rejected", "needs_revision", name="review_status"), default="pending")
    review_comments = Column(Text, nullable=True)
    reviewed_by = Column(String(255), nullable=True)
    review_date = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    research_items = relationship("ResearchItem", back_populates="article")
    social_posts = relationship("SocialPost", back_populates="article")
    visuals = relationship("Visual", back_populates="article")
    exports = relationship("ArticleExport", back_populates="article")

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

class ArticleExport(BaseModel):
    __tablename__ = "article_exports"
    
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    doc_id = Column(String(255), nullable=False)
    folder_id = Column(String(255), nullable=False)
    doc_url = Column(String(512), nullable=True)  # Store URL for easy access
    export_date = Column(DateTime(timezone=True), default=func.now())
    status = Column(Enum("pending_review", "approved", "rejected", "needs_revision", name="export_status"), default="pending_review")
    review_comments = Column(Text, nullable=True)
    reviewed_by = Column(String(255), nullable=True)
    review_date = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    article = relationship("Article", back_populates="exports")
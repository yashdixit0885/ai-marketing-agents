# models/content_models.py

from sqlalchemy import Column, String, Text, Integer, ForeignKey, Enum, Boolean, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Dict, Optional, Any
import uuid

class ResearchItem(BaseModel):
    __tablename__ = "research_items"
    
    title = Column(String(255), nullable=False)
    source = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    meta_data = Column(JSON, nullable=True)
    
    # Relationships
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=True)

class Article(BaseModel):
    __tablename__ = "articles"
    
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(Enum("draft", "review", "published"), default="draft")
    word_count = Column(Integer, nullable=True)
    
    # Add new review fields
    review_status = Column(Enum("pending", "approved", "rejected", "needs_revision"), default="pending")
    review_comments = Column(Text, nullable=True)
    reviewed_by = Column(String(255), nullable=True)
    review_date = Column(DateTime(timezone=True), nullable=True)

class SocialPost(BaseModel):
    __tablename__ = "social_posts"
    
    platform = Column(Enum("linkedin", "twitter", "medium", "substack"))
    content = Column(Text, nullable=False)
    status = Column(Enum("draft", "scheduled", "published"), default="draft")
    scheduled_time = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)

class Visual(BaseModel):
    __tablename__ = "visuals"
    
    type = Column(Enum("chart", "infographic", "quote_card", "other"))
    title = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=False)
    
    # Relationships
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)

class ArticleExport(BaseModel):
    __tablename__ = "article_exports"
    
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    doc_id = Column(String(255), nullable=False)
    folder_id = Column(String(255), nullable=False)
    doc_url = Column(String(512), nullable=True)  # Store URL for easy access
    export_date = Column(DateTime(timezone=True), default=func.now())
    status = Column(Enum("pending_review", "approved", "rejected", "needs_revision"), default="pending_review")
    review_comments = Column(Text, nullable=True)
    reviewed_by = Column(String(255), nullable=True)
    review_date = Column(DateTime(timezone=True), nullable=True)

# Add relationships after all classes are defined
ResearchItem.article = relationship("Article", foreign_keys=[ResearchItem.article_id], back_populates="research_items")
Article.research_items = relationship("ResearchItem", foreign_keys=[ResearchItem.article_id], back_populates="article")
Article.social_posts = relationship("SocialPost", foreign_keys=[SocialPost.article_id], back_populates="article")
SocialPost.article = relationship("Article", foreign_keys=[SocialPost.article_id], back_populates="social_posts")
Article.visuals = relationship("Visual", foreign_keys=[Visual.article_id], back_populates="article")
Visual.article = relationship("Article", foreign_keys=[Visual.article_id], back_populates="visuals")
Article.exports = relationship("ArticleExport", foreign_keys=[ArticleExport.article_id], back_populates="article")
ArticleExport.article = relationship("Article", foreign_keys=[ArticleExport.article_id], back_populates="exports")

class ContentType(str, PyEnum):
    ARTICLE = "article"
    BLOG_POST = "blog_post"
    NEWSLETTER = "newsletter"
    REPORT = "report"
    CASE_STUDY = "case_study"
    WHITE_PAPER = "white_paper"

class ContentTone(str, PyEnum):
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    TECHNICAL = "technical"
    CONVERSATIONAL = "conversational"
    FORMAL = "formal"
    INFORMAL = "informal"

class VisualType(str, PyEnum):
    HEADER_IMAGE = "header_image"
    CHART = "chart"
    INFOGRAPHIC = "infographic"
    QUOTE_CARD = "quote_card"
    DIAGRAM = "diagram"
    ILLUSTRATION = "illustration"

@dataclass
class ContentSection:
    title: str
    content: str
    keywords: List[str] = field(default_factory=list)
    order: int = 0

@dataclass
class VisualData:
    type: VisualType
    title: str
    description: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    url: Optional[str] = None
    drive_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    best_placement: Optional[str] = None  # Suggested section title for placement
    
    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type.value if isinstance(self.type, VisualType) else self.type,
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "drive_id": self.drive_id,
            "metadata": self.metadata,
            "best_placement": self.best_placement
        }

@dataclass
class ArticleData:
    title: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    subtitle: Optional[str] = None
    author: str = "AI Content Generator"
    content: str = ""
    summary: str = ""
    keywords: List[str] = field(default_factory=list)
    content_type: ContentType = ContentType.ARTICLE
    tone: ContentTone = ContentTone.PROFESSIONAL
    sections: List[ContentSection] = field(default_factory=list)
    references: List[Dict[str, str]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_section(self, title: str, content: str, keywords: List[str] = None):
        if keywords is None:
            keywords = []
        order = len(self.sections)
        self.sections.append(ContentSection(title=title, content=content, keywords=keywords, order=order))
        
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "subtitle": self.subtitle,
            "author": self.author, 
            "content": self.content,
            "summary": self.summary,
            "keywords": self.keywords,
            "content_type": self.content_type.value if isinstance(self.content_type, ContentType) else self.content_type,
            "tone": self.tone.value if isinstance(self.tone, ContentTone) else self.tone,
            "sections": [
                {
                    "title": section.title,
                    "content": section.content,
                    "keywords": section.keywords,
                    "order": section.order
                } 
                for section in self.sections
            ],
            "references": self.references,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }

@dataclass
class AtomicContentData:
    article_id: str 
    platform: str  # linkedin, twitter, medium, etc.
    content_type: str  # post, thread, carousel, etc.
    content: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: Optional[str] = None
    visual_ids: List[str] = field(default_factory=list)
    posting_schedule: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self):
        return {
            "id": self.id,
            "article_id": self.article_id,
            "platform": self.platform,
            "content_type": self.content_type,
            "content": self.content,
            "title": self.title,
            "visual_ids": self.visual_ids,
            "posting_schedule": self.posting_schedule.isoformat() if self.posting_schedule else None,
            "metadata": self.metadata
        }
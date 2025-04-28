from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from .base import BaseModel

class ContentPerformance(BaseModel):
    __tablename__ = "content_performance"
    
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    conversion_rate = Column(Float, default=0.0)
    
    # Relationships
    article = relationship("Article")
# services/dashboard/dashboard.py

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os
import logging

from models.content_models import Article, ArticleExport, SocialPost, Visual
from models import db_session

logger = logging.getLogger(__name__)

# Create dashboard directory structure
os.makedirs("services/dashboard/static", exist_ok=True)
os.makedirs("services/dashboard/templates", exist_ok=True)

def setup_dashboard(app: FastAPI):
    """Set up dashboard routes and static files."""
    
    # Set up static files and templates
    app.mount("/static", StaticFiles(directory="services/dashboard/static"), name="static")
    templates = Jinja2Templates(directory="services/dashboard/templates")
    
    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard(request: Request):
        """Render the dashboard."""
        articles = db_session.query(Article).all()
        exports = db_session.query(ArticleExport).all()
        
        # Count articles by status
        article_counts = {
            "draft": 0,
            "review": 0,
            "published": 0
        }
        
        review_counts = {
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "needs_revision": 0
        }
        
        for article in articles:
            if article.status in article_counts:
                article_counts[article.status] += 1
            
            if article.review_status in review_counts:
                review_counts[article.review_status] += 1
        
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "articles": articles,
                "exports": exports,
                "article_counts": article_counts,
                "review_counts": review_counts
            }
        )
    
    @app.get("/dashboard/article/{article_id}", response_class=HTMLResponse)
    async def article_detail(request: Request, article_id: int):
        """Render article detail page."""
        article = db_session.get(Article, article_id)
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        social_posts = db_session.query(SocialPost).filter(SocialPost.article_id == article_id).all()
        visuals = db_session.query(Visual).filter(Visual.article_id == article_id).all()
        exports = db_session.query(ArticleExport).filter(ArticleExport.article_id == article_id).all()
        
        return templates.TemplateResponse(
            "article_detail.html",
            {
                "request": request,
                "article": article,
                "social_posts": social_posts,
                "visuals": visuals,
                "exports": exports
            }
        )
    
    return app
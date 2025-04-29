import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from models import init_db
from config.celery import celery_app
from services.scheduling.scheduler import ContentScheduler
from fastapi import FastAPI, HTTPException, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from pydantic import BaseModel
import logging
from models import init_db
from config.celery import celery_app
from services.scheduling.scheduler import ContentScheduler
from services.review_handler import ReviewHandler
from agents.export_agent import ExportAgent
from agents.distribution_agent import DistributionAgent
from models.content_models import Article, ArticleExport
from models import db_session
from services.dashboard.dashboard import setup_dashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Content Automation")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and other components on startup."""
    logger.info("Initializing database")
    init_db()
    logger.info("Database initialized")
    yield


app = FastAPI(title="AI Content Automation", lifespan=lifespan)

# Define Pydantic models
class ExportRequest(BaseModel):
    article_id: int
    reviewer_email: Optional[str] = None

class ReviewRequest(BaseModel):
    export_id: int
    status: str
    comments: Optional[str] = None
    reviewer_name: str

class DistributeRequest(BaseModel):
    article_id: int



@app.get("/")
async def root():
    return {"message": "AI Content Automation API"}

@app.post("/schedule/weekly")
async def schedule_weekly():
    """Endpoint to schedule weekly content creation."""
    result = ContentScheduler.schedule_weekly_content()
    return {"message": result}

@app.post("/export")
async def export_article(request: ExportRequest):
    """Export an article to Google Docs for review."""
    try:
        export_agent = ExportAgent()
        export = await export_agent.run(request.article_id, request.reviewer_email)
        
        return {
            "status": "success",
            "export_id": export.id,
            "doc_url": export.doc_url,
            "message": f"Article exported successfully. Document URL: {export.doc_url}"
        }
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.post("/review")
async def process_review(request: ReviewRequest):
    """Process a review for an article."""
    try:
        if request.status not in ["approved", "rejected", "needs_revision"]:
            raise HTTPException(status_code=400, detail="Invalid status. Must be 'approved', 'rejected', or 'needs_revision'")
        
        review_handler = ReviewHandler()
        result = await review_handler.process_review(
            request.export_id,
            request.status,
            request.comments,
            request.reviewer_name
        )
        
        return {
            "status": "success",
            "review": result,
            "message": f"Review processed successfully. Article status: {request.status}"
        }
    except Exception as e:
        logger.error(f"Review processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Review processing failed: {str(e)}")

@app.post("/distribute")
async def distribute_article(request: DistributeRequest):
    """Distribute an approved article."""
    try:
        # Get the article to check approval status
        article = db_session.get(Article, request.article_id)
        if not article:
            raise HTTPException(status_code=404, detail=f"Article with ID {request.article_id} not found")
        
        if article.review_status != "approved":
            return {
                "status": "warning",
                "message": f"Cannot distribute: article has not been approved (status: {article.review_status})"
            }
        
        distribution_agent = DistributionAgent()
        posts = await distribution_agent.run(article_id=request.article_id)
        
        return {
            "status": "success",
            "posts_scheduled": len(posts),
            "message": f"Article distributed successfully. {len(posts)} posts scheduled."
        }
    except Exception as e:
        logger.error(f"Distribution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Distribution failed: {str(e)}")

@app.get("/articles")
async def get_articles():
    """Get all articles."""
    articles = db_session.query(Article).all()
    return [
        {
            "id": article.id,
            "title": article.title,
            "status": article.status,
            "review_status": article.review_status,
            "created_at": article.created_at,
            "word_count": article.word_count
        }
        for article in articles
    ]

@app.get("/exports")
async def get_exports():
    """Get all exports."""
    exports = db_session.query(ArticleExport).all()
    return [
        {
            "id": export.id,
            "article_id": export.article_id,
            "status": export.status,
            "doc_url": export.doc_url,
            "export_date": export.export_date,
            "review_date": export.review_date,
            "reviewed_by": export.reviewed_by
        }
        for export in exports
    ]

# Set up the dashboard
app = setup_dashboard(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
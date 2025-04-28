import logging
from fastapi import FastAPI
from models import init_db
from config.celery import celery_app
from services.scheduling.scheduler import ContentScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Content Automation")

@app.on_event("startup")
async def startup_event():
    """Initialize database and other components on startup."""
    logger.info("Initializing database")
    init_db()
    logger.info("Database initialized")

@app.get("/")
async def root():
    return {"message": "AI Content Automation API"}

@app.post("/schedule/weekly")
async def schedule_weekly():
    """Endpoint to schedule weekly content creation."""
    result = ContentScheduler.schedule_weekly_content()
    return {"message": result}

# Add more endpoints as needed

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
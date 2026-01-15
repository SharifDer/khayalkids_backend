import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from config import settings
from database import Database
from api import books, health, admin, previews

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Create directories BEFORE FastAPI app initialization
def create_directories():
    """Create all necessary directories on startup"""
    directories = [
        settings.STORIES_BASE_DIR,
        settings.TEMPLATES_DIR,
        settings.UPLOADS_DIR,
        settings.PREVIEWS_DIR,
        settings.GENERATED_DIR,
        settings.EXPORTS_DIR,
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"✓ Directory ensured: {directory}")


# Initialize directories immediately
create_directories()


# Initialize FastAPI app
app = FastAPI(
    title="KhayalKids API",
    description="AI-Powered Personalized Arabic Children's Storybooks",
    version="1.0.0",
)




@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("Starting KhayalKids API...")
    await Database.initialize()
    logger.info("✅ Application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info("Shutting down...")
    await Database.close()


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Mount static files (after directories are created)
app.mount("/stories", StaticFiles(directory=settings.STORIES_BASE_DIR), name="stories")



# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(books.router, prefix="/api", tags=["Books"])
app.include_router(admin.router, prefix="/api", tags=["Admin"])
app.include_router(previews.router, prefix="/api", tags=["Previews"])

@app.get("/")
async def root():
    return {
        "message": "KhayalKids API",
        "version": "1.0.0",
        "docs": "/docs"
    }

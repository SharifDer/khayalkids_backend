import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from config import settings
from database import Database
from api import books, health, admin, previews, orders
from services.face_detection_service import FaceDetectionService
import numpy as np
import tempfile
from deepface import DeepFace
from services.face_detection_service import FaceDetectionService
import threading
import schedule
import time
from services.snapshot_service import SnapshotService

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

def run_backup_scheduler(snapshot_service: SnapshotService):
    """Background thread for hourly snapshots"""
    # Run first backup immediately on startup
    logger.info("🔄 Running initial snapshot check...")
    snapshot_service.backup_job()
    
    # Schedule hourly backups at :00
    schedule.every().hour.at(":00").do(snapshot_service.backup_job)
    logger.info("⏰ Scheduled hourly snapshot checks")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


# Initialize directories immediately
create_directories()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting KhayalKids API...")
    await Database.initialize()
    
    # Preload AI models
    logger.info("🚀 Preloading AI models...")
    FaceDetectionService._get_yolo_model()
    try:
        import tempfile
        import cv2
        temp_img = np.zeros((224, 224, 3), dtype=np.uint8)
        fd, temp_path = tempfile.mkstemp(suffix='.jpg')
        os.close(fd)
        cv2.imwrite(temp_path, temp_img)
        DeepFace.represent(temp_path, model_name='Facenet512', enforce_detection=False)
        os.remove(temp_path)
        logger.info("✅ DeepFace Facenet512 preloaded")
    except Exception as e:
        logger.warning(f"DeepFace preload warning: {e}")
    
    logger.info("✅ All models preloaded")
    logger.info("✅ All models preloaded")
    if settings.HETZNER_API_TOKEN and settings.HETZNER_SERVER_NAME:
        logger.info("🔄 Starting snapshot backup scheduler...")
        snapshot_service = SnapshotService(
            api_token=settings.HETZNER_API_TOKEN,
            server_name=settings.HETZNER_SERVER_NAME
        )
        backup_thread = threading.Thread(
            target=run_backup_scheduler, 
            args=(snapshot_service,),
            daemon=True
        )
        backup_thread.start()
        logger.info("✅ Snapshot backup scheduler started")
    else:
        logger.warning("⚠️ Hetzner credentials missing - snapshot backups disabled")
    
    logger.info("✅ Application started successfully")
    
    yield  
    
    # Shutdown
    logger.info("Shutting down...")
    await Database.close()


# Initialize FastAPI app
app = FastAPI(
    title="KhayalKids API",
    description="AI-Powered Personalized Arabic Children's Storybooks",
    version="1.0.0",
    lifespan=lifespan
)



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
app.include_router(orders.router, prefix="/api" , tags=["Orders"])


@app.get("/")
async def root():
    return {
        "message": "KhayalKids API",
        "version": "1.0.0",
        "docs": "/docs"
    }

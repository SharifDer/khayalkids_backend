# API endpoint for preview generation
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException
from utils.file_utils import validate_uploaded_photo
import logging
import secrets
from datetime import datetime, timedelta

from repositories.preview_repo import PreviewRepository
from repositories.book_repo import BookRepository
from services.preview_generation_service import PreviewGenerationService
from schemas.responses import PreviewResponse, PreviewStatusResponse
from schemas.requests import ContactNotificationRequest
from repositories.contact_repo import ContactRepository


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/previews", response_model=PreviewResponse)
async def create_preview(
    background_tasks: BackgroundTasks,
    book_id: int = Form(...),
    child_name: str = Form(...),
    photo: UploadFile = File(...)
):
    """
    Generate preview with child's face swapped (first 3 pages only)
    """
    try:
        # Validate book exists
        book = await BookRepository.get_by_id(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        # Validate file size (10MB max)
        from config import settings
        content = await photo.read()
        if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"File too large (max {settings.MAX_UPLOAD_SIZE_MB}MB)")
        
        # Validate image format
        if not photo.content_type or not photo.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Generate unique preview token
        preview_token = secrets.token_urlsafe(16)
        
        # Save photo temporarily
        from utils.file_utils import save_upload_file
        photo_path = await save_upload_file(photo, content, preview_token)
        
        is_valid, error_message = validate_uploaded_photo(photo_path)
        # Create preview record in database
        preview_id = await PreviewRepository.create_preview(
            book_id=book_id,
            preview_token=preview_token,
            child_name=child_name,
            original_photo_path=photo_path,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        if not is_valid:
            await PreviewRepository.update_status(
                preview_id=preview_id,
                status="failed",
                error_message=error_message
            )
            raise HTTPException(status_code=400, detail=error_message)
        # Start background processing
        background_tasks.add_task(
            PreviewGenerationService.generate_preview,
            preview_id=preview_id,
            preview_token=preview_token,
            book_id=book_id,
            child_name=child_name,
            photo_path=photo_path
        )
        
        logger.info(f"Preview creation initiated: {preview_token}")
        
        return PreviewResponse(
            preview_token=preview_token,
            status="processing",
            estimated_time_seconds=90
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating preview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create preview")


@router.get("/previews/{preview_token}", response_model=PreviewStatusResponse)
async def get_preview_status(preview_token: str):
    """
    Check preview generation status and get image URLs
    """
    try:
        preview = await PreviewRepository.get_by_token(preview_token)
        
        if not preview:
            raise HTTPException(status_code=404, detail="Preview not found")
        
        # Check if expired
        if datetime.fromisoformat(preview['expires_at']) < datetime.utcnow():
            raise HTTPException(status_code=410, detail="Preview expired")
        
        return PreviewStatusResponse(
            status=preview['preview_status'],
            preview_images_urls=preview.get('swapped_images_paths'),
            error_message=preview.get('error_message')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching preview status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch preview status")


@router.post("/{preview_token}/phone_number")
async def add_contact_for_notification(
    preview_token: str,
    request: ContactNotificationRequest
):
    """
    Save phone_number to send notification when preview is ready.
    Should only be called during preview processing phase.
    """
    # Verify preview exists
    preview = await PreviewRepository.get_by_token(preview_token)
    if not preview:
        raise HTTPException(status_code=404, detail="Preview not found")
    
    # Check if already completed (optional validation)
    if preview.get("preview_status") == "completed":
        raise HTTPException(
            status_code=400, 
            detail="Preview already completed. Please use support icons to contact us."
        )
    
    # Save contact using class method
    await ContactRepository.create_contact(
        preview_token=preview_token,
        book_id=request.book_id,
        phone_number=request.phone_number
    )
    
    return {
        "message": "سنرسل لك رابط المعاينة على الواتساب عند الجاهزية",
        "preview_token": preview_token
    }
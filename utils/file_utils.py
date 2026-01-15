# File utilities
import os
import aiofiles
from pathlib import Path
from fastapi import UploadFile
import logging

from config import settings

logger = logging.getLogger(__name__)


async def save_upload_file(upload_file: UploadFile, content: bytes, preview_token: str) -> str:
    """
    Save uploaded file to uploads directory
    Returns: relative path from STORIES_BASE_DIR
    """
    # Create directory
    upload_dir = Path(settings.UPLOADS_DIR) / preview_token
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    ext = Path(upload_file.filename).suffix if upload_file.filename else ".jpg"
    filename = f"child_photo{ext}"
    filepath = upload_dir / filename
    
    # Save file
    async with aiofiles.open(filepath, 'wb') as f:
        await f.write(content)
    
    logger.info(f"File saved: {filepath}")
    
    # Return relative path for database
    return filepath.as_posix()

# Database operations for previews
from database import Database
from typing import Optional, Dict, Any
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class PreviewRepository:
    
    @staticmethod
    async def create_preview(
        book_id: int,
        preview_token: str,
        child_name: str,
        original_photo_path: str,
        expires_at: datetime,
        cartoon_photo_path: Optional[str] = None
    ) -> int:
        """Create new preview record"""
        query = """
            INSERT INTO previews (
                book_id, preview_token, child_name, original_photo_path, 
                cartoon_photo_path, preview_status, expires_at
            ) VALUES (?, ?, ?, ?, ?, 'processing', ?)
        """
        
        async with Database.connection() as conn:
            cursor = await conn.execute(
                query,
                (book_id, preview_token, child_name, original_photo_path, 
                 cartoon_photo_path, expires_at.isoformat())
            )
            await conn.commit()
            return cursor.lastrowid

    
    @staticmethod
    async def get_by_token(preview_token: str) -> Optional[Dict[str, Any]]:
        """Get preview by token"""
        query = "SELECT * FROM previews WHERE preview_token = ?"
        result = await Database.fetch_one(query, (preview_token,))
        
        if result and result.get('swapped_images_paths'):
            # Parse JSON array
            result['swapped_images_paths'] = json.loads(result['swapped_images_paths'])
        
        return result
    
    @staticmethod
    async def get_by_id(preview_id: int) -> Optional[Dict[str, Any]]:
        """Get preview by ID"""
        query = "SELECT * FROM previews WHERE id = ?"
        return await Database.fetch_one(query, (preview_id,))
    
    @staticmethod
    async def update_status(
        preview_id: int,
        status: str,
        swapped_images_paths: Optional[list] = None,
        error_message: Optional[str] = None,
        cartoon_photo_path: Optional[str] = None
    ):
        """Update preview status and results"""
        query = """
            UPDATE previews 
            SET preview_status = ?, 
                swapped_images_paths = ?,
                error_message = ?,
                cartoon_photo_path = ?
            WHERE id = ?
        """
        
        images_json = json.dumps(swapped_images_paths) if swapped_images_paths else None
        
        await Database.execute(
            query,
            (status, images_json, error_message, cartoon_photo_path, preview_id)
        )
        
        logger.info(f"Preview {preview_id} status updated to: {status}")

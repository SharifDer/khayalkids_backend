# Database operations for generated books
from database import Database
from typing import Optional, Dict, Any, List
import json
import logging
from datetime import datetime
from utils.file_utils import truncate_error_message

logger = logging.getLogger(__name__)


class GeneratedBookRepository:
    
    @staticmethod
    async def create_generated_book(
        order_id: int,
        original_photo_path: str
    ) -> int:
        """Create new generated book record"""
        query = """
            INSERT INTO generated_books (
                order_id, original_photo_path, generation_status,
                characters_completed, estimated_time_minutes
            ) VALUES (?, ?, 'queued', 0, 5)
        """
        
        async with Database.connection() as conn:
            cursor = await conn.execute(query, (order_id, original_photo_path))
            await conn.commit()
            generated_book_id = cursor.lastrowid
        
        logger.info(f"Generated book record created for order {order_id}")
        return generated_book_id
    
    @staticmethod
    async def get_by_order_id(order_id: int) -> Optional[Dict[str, Any]]:
        """Get generated book by order ID"""
        query = "SELECT * FROM generated_books WHERE order_id = ?"
        result = await Database.fetch_one(query, (order_id,))
        
        if result and result.get('swapped_images_paths'):
            result['swapped_images_paths'] = json.loads(result['swapped_images_paths'])
        
        return result
    
    @staticmethod
    async def update_status(
        order_id: int,
        status: str,
        error_message: Optional[str] = None
    ):
        """Update generation status"""
        query = """
            UPDATE generated_books 
            SET generation_status = ?,
                error_message = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE order_id = ?
        """
        truncated_error = truncate_error_message(error_message)

        await Database.execute(query, (status, truncated_error, order_id))
        logger.info(f"Generated book {order_id} status: {status}")
    
    @staticmethod
    async def update_progress(
        order_id: int,
        characters_completed: int,
        estimated_time_minutes: int
    ):
        """Update processing progress"""
        query = """
            UPDATE generated_books 
            SET characters_completed = ?,
                estimated_time_minutes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE order_id = ?
        """
        
        await Database.execute(
            query,
            (characters_completed, estimated_time_minutes, order_id)
        )
    
    @staticmethod
    async def mark_processing_started(order_id: int):
        """Mark processing as started"""
        query = """
            UPDATE generated_books 
            SET generation_status = 'processing',
                processing_started_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE order_id = ?
        """
        await Database.execute(query, (order_id,))
    
    @staticmethod
    async def update_final_paths(
        order_id: int,
        final_pptx_path: str,
        final_pdf_path: str,
        swapped_images_paths: list
    ):
        """Update final file paths and mark as completed"""
        query = """
            UPDATE generated_books 
            SET final_pptx_path = ?,
                final_pdf_path = ?,
                swapped_images_paths = ?,
                generation_status = 'completed',
                processing_completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE order_id = ?
        """
        
        images_json = json.dumps(swapped_images_paths)
        
        await Database.execute(
            query,
            (final_pptx_path, final_pdf_path, images_json, order_id)
        )
        
        logger.info(f"Generated book {order_id} completed")
    @staticmethod
    async def get_all_generated_books(since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get all generated books with optional time filter"""
        if since:
            query = """
                SELECT gb.*, o.order_number, o.child_name, o.customer_name,
                    b.title as book_title, b.gender as book_gender
                FROM generated_books gb
                LEFT JOIN orders o ON gb.order_id = o.id
                LEFT JOIN books b ON o.book_id = b.id
                WHERE gb.created_at >= ?
                ORDER BY gb.created_at DESC
            """
            results = await Database.fetch_all(query, (since.isoformat(),))
        else:
            query = """
                SELECT gb.*, o.order_number, o.child_name, o.customer_name,
                    b.title as book_title, b.gender as book_gender
                FROM generated_books gb
                LEFT JOIN orders o ON gb.order_id = o.id
                LEFT JOIN books b ON o.book_id = b.id
                ORDER BY gb.created_at DESC
            """
            results = await Database.fetch_all(query)
        
        # Parse JSON fields
        for result in results:
            if result.get('swapped_images_paths'):
                result['swapped_images_paths'] = json.loads(result['swapped_images_paths'])
        
        return results

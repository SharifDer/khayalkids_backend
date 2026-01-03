import json
from typing import List, Optional, Dict, Any
from database import Database
from schemas.responses import BookResponse, BookDetailResponse
import logging

logger = logging.getLogger(__name__)


class BookRepository:
    
    @staticmethod
    async def get_all_active(
    ) -> List[BookResponse]:
        """Get all active books with optional filters"""
        
        query = "SELECT * FROM books WHERE is_active = 1"
        params = []    
        query += " ORDER BY created_at DESC"
        
        rows = await Database.fetch_all(query, tuple(params))
        
        return [BookRepository._row_to_response(row) for row in rows]
    
    @staticmethod
    async def get_by_id(book_id: int) -> Optional[BookDetailResponse]:
        """Get book by ID with all details"""
        
        query = "SELECT * FROM books WHERE id = ? AND is_active = 1"
        row = await Database.fetch_one(query, (book_id,))
        
        if not row:
            return None
        
        return BookRepository._row_to_detail_response(row)
    
    @staticmethod
    def _row_to_response(row: Dict[str, Any]) -> BookResponse:
        """Convert DB row to BookResponse"""
        return BookResponse(
            id=row['id'],
            title=row['title'],
            description=row['description'],
            age_range=row['age_range'],
            price=row['price'],
            cover_image_url=f"/{row['cover_image_path']}" if row['cover_image_path'] else None
        )
    
    @staticmethod
    def _row_to_detail_response(row: Dict[str, Any]) -> BookDetailResponse:
        """Convert DB row to BookDetailResponse with preview images"""
        
        # Parse preview images JSON
        preview_images = []
        if row['preview_images']:
            try:
                preview_paths = json.loads(row['preview_images'])
                preview_images = [
                     f"/{path}" 
                    for path in preview_paths
                ]
            except json.JSONDecodeError:
                logger.warning(f"Invalid preview_images JSON for book {row['id']}")
        
        return BookDetailResponse(
            id=row['id'],
            title=row['title'],
            description=row['description'],
            age_range=row['age_range'],
            price=row['price'],
            cover_image_url=f"/{row['cover_image_path']}" if row['cover_image_path'] else None,
            preview_images_urls=preview_images
        )
    
    @staticmethod
    async def create(book_data: dict) -> int:
        """Create new book, return book_id"""
        query = """
            INSERT INTO books (title, description, age_range, gender, price, template_path)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (
            book_data['title'],
            book_data['description'],
            book_data['age_range'],
            book_data['gender'],
            book_data['price'],
            "placeholder"  # Will be updated by update_paths() immediately after
        )
        
        async with Database.connection() as conn:
            cursor = await conn.execute(query, params)
            await conn.commit()
            return cursor.lastrowid


    @staticmethod
    async def update_paths(
        book_id: int,
        template_path: str,
        cover_image_path: str,
        preview_images: list[str]
    ):
        query = """
        UPDATE books
        SET
            template_path = ?,
            cover_image_path = ?,
            preview_images = ?
        WHERE id = ?
        """

        await Database.execute(
            query,
            (
                template_path,
                cover_image_path,
                json.dumps(preview_images),
                book_id
            )
        )

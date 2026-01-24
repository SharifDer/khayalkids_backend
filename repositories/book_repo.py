# In repositories/book_repo.py

import json
from typing import List, Optional, Dict, Any
from pathlib import Path
from database import Database
from schemas.responses import BookResponse, BookDetailResponse
import logging

logger = logging.getLogger(__name__)

class BookRepository:
    
    @staticmethod
    def parse_reference_paths(book_record) -> List[Path]:
        """
        Parse character_reference_image_url from BookDetailResponse
        Field is already a list of paths (parsed in _row_to_detail_response)
        """
        reference_field = book_record.character_reference_image_url
        
        if not reference_field:
            return []
        
        if isinstance(reference_field, list):
            return [Path(p.lstrip('/')) for p in reference_field if p]
        return []

    
    @staticmethod
    async def get_all_active(limit_per_gender: Optional[int] = None) -> List[BookResponse]:
        """Get all active books with optional limit per gender"""
        
        if limit_per_gender is None:
            # Return all books
            query = "SELECT * FROM books WHERE is_active = 1 ORDER BY created_at ASC"
            rows = await Database.fetch_all(query)
        else:
            # Return first N books per gender
            query = """
                SELECT * FROM (
                    SELECT *, ROW_NUMBER() OVER (PARTITION BY gender ORDER BY created_at ASC) as rn
                    FROM books 
                    WHERE is_active = 1
                ) WHERE rn <= ?
                ORDER BY gender, created_at ASC
            """
            rows = await Database.fetch_all(query, (limit_per_gender,))
        
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
            gender=row["gender"],
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
                preview_images = [f"/{path}" for path in preview_paths]
            except json.JSONDecodeError:
                logger.warning(f"Invalid preview_images JSON for book {row['id']}")
        
        # Parse character reference images JSON
        character_references = []
        if row['character_reference_image_url']:
            try:
                reference_paths = json.loads(row['character_reference_image_url'])
                character_references = [f"/{path}" for path in reference_paths]
            except json.JSONDecodeError:
                logger.warning(f"Invalid character_reference_image_url JSON for book {row['id']}")
        
        return BookDetailResponse(
            id=row['id'],
            title=row['title'],
            description=row['description'],
            age_range=row['age_range'],
            price=row['price'],
            gender=row["gender"],
            cover_image_url=f"/{row['cover_image_path']}" if row['cover_image_path'] else None,
            hero_name=row["hero_name"],
            character_reference_image_url=character_references, 
            preview_images_urls=preview_images
        )

    
    @staticmethod
    async def create(book_data: dict) -> int:
        """Create new book, return book_id"""
        query = """
            INSERT INTO books (title, description, age_range, gender, price, hero_name, template_path, character_reference_image_url)
            VALUES (?, ?, ?, ?, ?, ?, ? , ?)
        """
        params = (
            book_data['title'],
            book_data['description'],
            book_data['age_range'],
            book_data['gender'],
            book_data['price'],
            book_data['hero_name'],
            "placeholder",  # Will be updated by update_paths() immediately after
            "placeholder"
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
        character_reference_image_urls: List[str],  # ✨ CHANGED: Now accepts list
        preview_images: list[str]
    ):
        """Update file paths for book, storing references as JSON array"""
        query = """
        UPDATE books
        SET
            template_path = ?,
            cover_image_path = ?,
            character_reference_image_url = ?,
            preview_images = ?
        WHERE id = ?
        """

        await Database.execute(
            query,
            (
                template_path,
                cover_image_path,
                json.dumps(character_reference_image_urls),  # ✨ CHANGED: Store as JSON
                json.dumps(preview_images),
                book_id
            )
        )
    @staticmethod
    async def update(book_id: int, updates: dict):
        """Update book fields dynamically"""
        if not updates:
            return
        
        # Build dynamic query
        fields = ", ".join([f"{key} = ?" for key in updates.keys()])
        query = f"UPDATE books SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        
        params = tuple(updates.values()) + (book_id,)
        await Database.execute(query, params)

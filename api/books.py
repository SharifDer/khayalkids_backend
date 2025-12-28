from fastapi import APIRouter, HTTPException
from typing import List, Optional
from schemas.responses import BookResponse, BookDetailResponse
from repositories.book_repo import BookRepository
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/books", response_model=List[BookResponse])
async def get_books(
    age_range: Optional[str] = None,
    category: Optional[str] = None
):
    """
    Get all active books with optional filtering
    
    Query params:
    - age_range: Filter by age range (e.g., "0-3", "4-6", "7-10")
    - category: Filter by category (e.g., "adventure", "educational")
    """
    try:
        books = await BookRepository.get_all_active(
            age_range=age_range,
            category=category
        )
        return books
    except Exception as e:
        logger.error(f"Error fetching books: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch books")


@router.get("/books/{book_id}", response_model=BookDetailResponse)
async def get_book_detail(book_id: int):
    """
    Get detailed information about a specific book including preview images
    """
    try:
        book = await BookRepository.get_by_id(book_id)
        
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        return book
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching book {book_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch book details")

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from schemas.responses import BookResponse, BookDetailResponse
from repositories.book_repo import BookRepository
import logging
from fastapi import Response

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/get_books", response_model=List[BookResponse])
async def get_books(
    response : Response,
    limit_per_gender: Optional[int] = None):
    """
    Get all active books, optionally limited per gender
    
    Args:
        limit_per_gender: If provided, returns first N books per gender (e.g., 3)
    """
    response.headers["Cache-Control"] = "public, max-age=180"  
    try:
        books = await BookRepository.get_all_active(limit_per_gender=limit_per_gender)
        return books
    except Exception as e:
        logger.error(f"Error fetching books: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch books")


@router.get("/get_book_details/{book_id}", response_model=BookDetailResponse)
async def get_book_detail(
    response : Response,
    book_id: int):
    """
    Get detailed information about a specific book including preview images
    """
    response.headers["Cache-Control"] = "public, max-age=180"
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

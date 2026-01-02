
from fastapi import APIRouter
from schemas.requests import CreateBookRequest
from repositories.book_repo import BookRepository

router = APIRouter()

@router.post("/admin/books")
async def create_book(request: CreateBookRequest):
    book_id = await BookRepository.create(request)

    return {
        "book_id": book_id,
        "message": "Book created"
    }

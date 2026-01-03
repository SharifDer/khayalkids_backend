from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class HealthResponse(BaseModel):
    status: str
    database: str


class BookResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    age_range: Optional[str] = None
    price: float
    cover_image_url: Optional[str] = None


class BookDetailResponse(BookResponse):
    preview_images_urls: List[str] = Field(default_factory=list)

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
    hero_name : str
    character_reference_image_url : str


class BookDetailResponse(BookResponse):
    preview_images_urls: List[str] = Field(default_factory=list)


class PreviewResponse(BaseModel):
    preview_token: str
    status: str  # "processing"
    estimated_time_seconds: int


class PreviewStatusResponse(BaseModel):
    status: str  # "processing" | "completed" | "failed"
    preview_images_urls: Optional[List[str]] = None
    error_message: Optional[str] = None
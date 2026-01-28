from pydantic import BaseModel, Field
from typing import Optional, List, Literal
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
    gender: Literal["male", "female"] 
    cover_image_url: Optional[str] = None
  
    

class BookDetailResponse(BookResponse):
    hero_name : str
    character_reference_image_url : List[str] = Field(default_factory=list)
    preview_images_urls: List[str] = Field(default_factory=list)

class PreviewResponse(BaseModel):
    preview_token: str
    status: str  # "processing"
    estimated_time_seconds: int


class PreviewStatusResponse(BaseModel):
    status: str  # "processing" | "completed" | "failed"
    preview_images_urls: Optional[List[str]] = None
    error_message: Optional[str] = None



class CreateOrderResponse(BaseModel):
    order_number: str
    total_amount: float
    currency: str
    message: str 

class OrderStatusResponse(BaseModel):
    order_number: str
    order_status: str
    payment_status: str
    generation_status: str
    characters_completed: int
    estimated_time_minutes: int
    final_pdf_url: Optional[str] = None
    error_message: Optional[str] = None

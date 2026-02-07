from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict
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
    child_name : Optional[str] = None
    book_title : Optional[str] = None
    book_description : Optional[str] = None
    




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




class PreviewDetail(BaseModel):
    id: int
    book_id: int
    book_title: Optional[str] = None
    book_gender: Optional[str] = None
    preview_token: str
    child_name: str
    original_photo_path: str
    cartoon_photo_path: Optional[str] = None
    preview_pptx_path: Optional[str] = None
    preview_pdf_path: Optional[str] = None
    swapped_images_paths: Optional[List[str]] = None
    preview_status: str
    error_message: Optional[str] = None
    expires_at: str
    created_at: str


class OrderDetail(BaseModel):
    id: int
    book_id: int
    book_title: Optional[str] = None
    book_gender: Optional[str] = None
    preview_id: Optional[int] = None
    preview_token: Optional[str] = None
    order_number: str
    child_name: str
    customer_name: str
    customer_email: str
    customer_phone: Optional[str] = None
    shipping_address: Optional[str] = None
    shipping_country: Optional[str] = None
    national_address_code: Optional[str] = None
    total_amount: float
    display_currency: str
    display_amount: Optional[float] = None
    payment_status: str
    payment_method: str
    order_status: str
    created_at: str
    updated_at: str


class ContactDetail(BaseModel):
    id: int
    preview_token: str
    book_id: int
    book_title: Optional[str] = None
    child_name: Optional[str] = None
    phone_number: str
    message_sent: int
    submitted_at: str


class GeneratedBookDetail(BaseModel):
    id: int
    order_id: int
    order_number: Optional[str] = None
    child_name: Optional[str] = None
    customer_name: Optional[str] = None
    book_title: Optional[str] = None
    book_gender: Optional[str] = None
    original_photo_path: str
    swapped_images_paths: Optional[List[str]] = None
    final_pptx_path: Optional[str] = None
    final_pdf_path: Optional[str] = None
    generation_status: str
    characters_completed: int
    estimated_time_minutes: Optional[int] = None
    error_message: Optional[str] = None
    retry_count: int
    processing_started_at: Optional[str] = None
    processing_completed_at: Optional[str] = None
    created_at: str
    updated_at: str


class StatsSummary(BaseModel):
    total_previews: int
    previews_by_status: Dict[str, int]
    total_orders: int
    orders_by_status: Dict[str, int]
    orders_by_payment_status: Dict[str, int]
    total_generated_books: int
    generated_books_by_status: Dict[str, int]
    total_contacts: int
    contacts_messages_sent: int
    contacts_messages_pending: int


class AdminStatsResponse(BaseModel):
    summary: StatsSummary
    previews: List[PreviewDetail]
    orders: List[OrderDetail]
    generated_books: List[GeneratedBookDetail]
    contacts: List[ContactDetail]
    time_filter: Optional[str] = None  # e.g., "last_7_days" or "last_24_hours"

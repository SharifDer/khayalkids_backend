from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
class CreateBookRequest(BaseModel):
    title: str
    description: str
    age_range: str
    gender: Literal["male", "female"]
    price: float
    hero_name: str


class CreateOrderRequest(BaseModel):
    preview_token: str = Field(..., description="Preview token from successful preview generation")
    customer_name: str = Field(..., min_length=2, max_length=100)
    customer_email: Optional[EmailStr] = None  
    customer_phone: str = Field(..., max_length=20)  
    shipping_address: str = Field(..., max_length=500)
    shipping_country: str = Field(description="ISO country code") 
    national_address_code: Optional[str] = Field(
        None, 
        min_length=8, 
        max_length=8,
        description="Saudi National Address Short Code (8 characters)"
    )  
    display_currency: str = Field(default="SAR", max_length=3)
    display_amount: float

class UpdateBookRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    age_range: Optional[str] = None
    gender: Optional[Literal["male", "female"]] = None
    price: Optional[float] = None
    hero_name: Optional[str] = None



class WhatsAppNotificationRequest(BaseModel):
    book_id: int = Field(..., description="Book ID for generating shareable link")
    whatsapp_number: str = Field( max_length=20, description="WhatsApp number with country code")
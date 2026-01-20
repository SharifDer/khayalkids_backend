from pydantic import BaseModel, EmailStr, Field
from typing import Literal
from typing import Optional
class CreateBookRequest(BaseModel):
    title: str
    description: str
    age_range: str
    gender: Literal["male", "female"]
    price: float
    hero_name: str


class CreateOrderRequest(BaseModel):
    preview_token: str = Field(..., description="Preview token from successful preview generation")
    child_age: Optional[int] = Field(None, ge=0, le=18, description="Child's age")
    customer_name: str = Field(..., min_length=2, max_length=100)
    customer_email: EmailStr
    customer_phone: Optional[str] = Field(None, max_length=20)
    shipping_address: Optional[str] = Field(None, max_length=500)
    shipping_country: Optional[str] = Field(None, max_length=2, description="ISO country code")
from pydantic import BaseModel
from typing import Literal

class CreateBookRequest(BaseModel):
    title: str
    description: str
    age_range: str
    gender: Literal["male", "female"]
    price: float
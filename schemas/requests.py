from pydantic import BaseModel

class CreateBookRequest(BaseModel):
    title: str
    description: str
    age_range: str
    gender: str
    price: float

from pydantic import BaseModel

class CreateBookRequest(BaseModel):
    title: str
    description: str
    age_range: int
    gender: str
    price: float

from fastapi import APIRouter
from database import Database
from schemas.responses import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    db_status = await Database.health_check()
    
    return HealthResponse(
        status="healthy" if db_status else "unhealthy",
        database="ok" if db_status else "error"
    )

import json
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "data/khayalkids.db"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # File Storage - All under stories/
    STORIES_BASE_DIR: str = "stories"
    TEMPLATES_DIR: str = "stories/templates"
    UPLOADS_DIR: str = "stories/uploads"
    PREVIEWS_DIR: str = "stories/previews"
    GENERATED_DIR: str = "stories/generated"
    EXPORTS_DIR: str = "stories/exports"
    
    # Upload limits
    MAX_UPLOAD_SIZE_MB: int = 10
    
    # CORS
    ALLOWED_ORIGINS: str = "*"
    
    # API Keys (loaded from JSON)
    FACESWAPPING_API: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    
    class Config:
        extra = "allow"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Load face swapping API key
        faceswap_key_file = Path("keys/facewow_key.json")
        with open(faceswap_key_file) as f:
            data = json.load(f)
            self.FACESWAPPING_API = data.get("FaceWow_Api", "")
    
   

settings = Settings()

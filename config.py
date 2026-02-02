import json
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Dict, Any

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
    SEGMIND_API_KEY: str = ""
    PRICING_CONFIG : Dict[str, Dict[str,float]]= {
        "SAR": {
            "rate": 1.0,
            "adjustment": 0
        },
        "YER": {
            "rate": 140.0,
            "adjustment": -30  
        }
    }
    TWILIO_ACCOUNT_SID : str = ""
    TWILIO_AUTH_TOKEN : str = "" 
    TWILIO_NUMBER_FROM : str = ""
    admin_password : str = ""
    FRONTEND_BASE_URL : str = "https://khayalkids.com"
    nano_banana_cartoon_prompt : str = """
    Convert the provided child photo into a storybook-style illustrated portrait suitable for high-quality children’s book illustrations.
        PRIMARY GOAL

        Preserve the child’s exact facial identity while rendering them in a semi-realistic storybook illustration style.
        IDENTITY (HIGHEST PRIORITY)

        Preserve exact facial structure: eye shape and spacing, nose shape, mouth shape, cheeks, jawline.

        Do not generalize, average, beautify, or stylize facial features.

        The result must clearly be the same child.
        STYLE REQUIREMENTS

        Semi-realistic children’s storybook illustration.

        Soft volumetric lighting.

        Gentle gradients and depth.

        Illustrated (not photographic) skin shading.

        Painterly but controlled.

        No flat or vector look.

        No avatar or sticker appearance.
        HAIR REQUIREMENTS

        Preserve the child’s real hairstyle, hairline, volume, and direction.

        Render hair with illustrated depth and soft strand definition.

        Do not invent or modify the hairstyle.
        BACKGROUND

        Clean, simple, neutral, softly blurred or solid pastel background.

        No objects, scenery, textures, or visual noise.
        FORBIDDEN

        Flat cartoon style, vector art, avatar style, sticker look, anime, exaggerated Pixar or Disney features, simplified facial features, generic child face, face averaging, beauty filters, artistic reinterpretation of identity.
        OUTPUT

        A clean, identity-accurate, storybook-quality illustrated portrait that can seamlessly blend into semi-realistic children’s book illustrations.
        """
    
    class Config:
        extra = "allow"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Load Segmind API key
        segmind_key_file = Path("keys/segmind_key.json")
        if segmind_key_file.exists():
            with open(segmind_key_file) as f:
                data = json.load(f)
                self.SEGMIND_API_KEY = data.get("api_key")
        twilio_key_file = Path("keys/twilio_key.json")
        if twilio_key_file.exists():
            with open(twilio_key_file) as f:
                data = json.load(f)
                self.TWILIO_ACCOUNT_SID = data.get("account_sid")
                self.TWILIO_AUTH_TOKEN = data.get("auth_token")
                self.TWILIO_NUMBER_FROM = data.get("number_from")
        admin_password_file = Path("keys/admin.json")
        with open(admin_password_file) as f:
            data = json.load(f)
            self.admin_password = data.get("admin_pass")
                

settings = Settings()

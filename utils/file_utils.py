# File utilities
import aiofiles
from pathlib import Path
from fastapi import UploadFile
import logging
import cv2
import numpy as np
from config import settings
from PIL import Image
import io
from fastapi import UploadFile

logger = logging.getLogger(__name__)


async def save_upload_file(upload_file: UploadFile, content: bytes, preview_token: str) -> str:
    """
    Save uploaded file to uploads directory
    Returns: relative path from STORIES_BASE_DIR
    """
    # Create directory
    upload_dir = Path(settings.UPLOADS_DIR) / preview_token
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    ext = Path(upload_file.filename).suffix if upload_file.filename else ".jpg"
    filename = f"child_photo{ext}"
    filepath = upload_dir / filename
    
    # Save file
    async with aiofiles.open(filepath, 'wb') as f:
        await f.write(content)
    
    logger.info(f"File saved: {filepath}")
    
    # Return relative path for database
    return filepath.as_posix()


def validate_uploaded_photo(photo_path: str) -> tuple[bool, str]:
    """
    Fast photo validation (~500ms using OpenCV)
    Catches: blur, multiple faces, low resolution
    """
    try:
        img = cv2.imread(photo_path)
        if img is None:
            return False, "فشل في قراءة الصورة. تأكد من أن الملف صورة صحيحة"
        
        h, w = img.shape[:2]
        
        # 1. Resolution check
        if h < 600 or w < 600:
            return False, "الصورة صغيرة جداً (الحد الأدنى 600×600). قد تكون الصورة مقصوصة أو ذات جودة منخفضة"
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 2. Blur detection
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        logger.info(f"Blur score: {blur_score}")
        if blur_score < 100:
            return False, "الصورة غير واضحة. قد تكون الكاميرا غير مركزة أو هناك حركة أثناء التصوير"
        
        # 3. Face detection
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        faces = face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.05,
            minNeighbors=5,
            minSize=(100, 100)
        )
        
        # 4. Check for faces
        if len(faces) == 0:
            return False, "لم نتمكن من إيجاد وجه واضح. تأكد من أن الوجه مواجه للكاميرا والإضاءة جيدة"
        
        if len(faces) > 1:
            return False, "يوجد أكثر من وجه في الصورة، أو أشياء كثيرة حول الوجه. الرجاء رفع صورة واضحة لطفل واحد فقط"
        
        # 5. Brightness check
        brightness = np.mean(gray)
        logger.info(f"Brightness: {brightness}")
        if brightness < 40:
            return False, "الصورة مظلمة جداً. حاول التصوير في مكان أكثر إضاءة"
        
        return True, "OK"
        
    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        return False, "خطأ في معالجة الصورة. تأكد من صيغة الملف"



def compress_image(upload_file: UploadFile, max_width: int = 1000, quality: int = 90) -> bytes:
    """
    Compress image to max_width with quality setting.
    Quality 90: Near-perfect visual quality, ~200-250KB for book covers
    """
    # Read uploaded file
    image_data = upload_file.file.read()
    img = Image.open(io.BytesIO(image_data))
    
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
    
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=quality, optimize=True)
    return buffer.getvalue()

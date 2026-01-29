import logging
import base64
import io
import requests
from pathlib import Path
from PIL import Image
from config import settings
from utils.profiler import profile


logger = logging.getLogger(__name__)


class CartoonificationService:
    
    @staticmethod
    @profile
    def cartoonify_photo(original_photo_path: str, output_path: str) -> str:
        """
        Convert real child photo to cartoon style using Segmind Nano Banana Pro API
        """
        try:
            # Step 1: Upload image to Segmind storage to get a URL
            image_url = CartoonificationService._upload_to_segmind_storage(original_photo_path)
            
            # Step 2: Call Nano Banana Pro API - OFFICIAL ENDPOINT
            url = "https://api.segmind.com/v1/nano-banana-pro"
            headers = {
                "x-api-key": settings.SEGMIND_API_KEY,
                "Content-Type": "application/json"
            }
            
            # Prompt for cartoonification
            prompt = settings.nano_banana_cartoon_prompt
            
            # OFFICIAL PARAMETERS FROM DOCUMENTATION
            data = {
                "prompt": prompt,
                "image_urls": [image_url],
                "aspect_ratio": "1:1",
                "output_resolution": "1K",
                "output_format": "jpg"
            }
            
            # Generate
            response = requests.post(url, headers=headers, json=data, timeout=180)
            
            if response.status_code != 200:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                raise ValueError(f"Segmind API error: {response.status_code} - {response.text}")
            
            # Step 3: Extract image from response
            # Documentation says "Returns: Image" but example shows response.json()
            # Need to check response content type
            content_type = response.headers.get('Content-Type', '')
            
            if 'application/json' in content_type:
                result = response.json()
                logger.info(f"JSON response received: {result}")
                # Response format is unclear from docs - handle the actual structure
                # This needs to be verified with actual API response
                raise ValueError(f"Received JSON response but format is unclear. Response: {result}")
            else:
                # Binary image response
                image_data = response.content
            
            # Convert to PIL Image and save
            cartoon_image = Image.open(io.BytesIO(image_data))
            
            # Save cartoonified image
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            cartoon_image.save(output_path)
            
            logger.info(f"Photo cartoonified successfully: {output_path}")
            return str(output_path)
                
        except Exception as e:
            logger.error(f"Cartoonification error: {e}", exc_info=True)
            raise
    
    @staticmethod
    def _upload_to_segmind_storage(image_path: str) -> str:
        """
        Upload image to Segmind storage and return the URL
        """
        try:
            # Read and encode image as base64
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            b64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Determine image format
            img = Image.open(image_path)
            image_format = img.format.lower() if img.format else 'jpeg'
            
            # Create data URL
            data_url = f"data:image/{image_format};base64,{b64_image}"
            
            # Upload to Segmind storage
            upload_url = "https://workflows-api.segmind.com/upload-asset"
            headers = {
                "x-api-key": settings.SEGMIND_API_KEY,
                "Content-Type": "application/json",
                "accept": "application/json"
            }
            
            payload = {
                "data_urls": [data_url]
            }
            
            upload_response = requests.post(upload_url, headers=headers, json=payload)
            
            if upload_response.status_code != 200:
                raise ValueError(f"Upload failed: {upload_response.status_code} - {upload_response.text}")
            
            # Extract the uploaded image URL
            upload_result = upload_response.json()
            
            if isinstance(upload_result, dict) and 'file_urls' in upload_result:
                return upload_result['file_urls'][0]
            else:
                raise ValueError(f"Unexpected upload response format: {upload_result}")
                
        except Exception as e:
            logger.error(f"Image upload error: {e}", exc_info=True)
            raise

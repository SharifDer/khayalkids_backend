import logging
import base64
import asyncio
import aiofiles
import aiohttp
from pathlib import Path
from config import settings
from utils.profiler import profile
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class FaceSwapService:
    
    API_ENDPOINT = "https://api.segmind.com/v1/faceswap-v5"
    POLL_INTERVAL = 3  # seconds
    MAX_RETRIES = 40  # 120 seconds total timeout
    _executor = ThreadPoolExecutor(max_workers=4)
    
    @staticmethod
    async def _to_base64(file_path: str) -> str:
        """Convert image to base64 - runs in thread pool to avoid blocking"""
        def _sync_encode():
            with open(file_path, "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(FaceSwapService._executor, _sync_encode)
    
    @staticmethod
    @profile
    async def swap_face(
        session: aiohttp.ClientSession,
        child_photo_path: str,
        character_crop_path: str,
        output_dir: str
    ) -> str:
        """Swap face using Segmind FaceSwap v5 API - fully async"""
        try:
            logger.info(f"🚀 swap_face ENTERED for {character_crop_path}")
            
            # Convert images to base64
            source_b64, target_b64 = await asyncio.gather(
                FaceSwapService._to_base64(child_photo_path),
                FaceSwapService._to_base64(character_crop_path)
            )
            
            payload = {
                "source_image": source_b64,
                "target_image": target_b64,
                "image_format": "png",
                "quality": 95,
                "seed": 42
            }
            
            headers = {
                'x-api-key': settings.SEGMIND_API_KEY,
                'Content-Type': 'application/json'
            }
            
            # Call API (Segmind returns image directly, not async task)
            async with session.post(
                FaceSwapService.API_ENDPOINT,
                json=payload,
                headers=headers
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise ValueError(f"Segmind API error: {error_text}")
                
                img_data = await resp.read()
            
            # Save result
            import hashlib
            file_hash = hashlib.md5(character_crop_path.encode()).hexdigest()[:8]
            output_path = Path(output_dir) / f"swapped_{file_hash}.jpg"
            
            async with aiofiles.open(output_path, "wb") as f:
                await f.write(img_data)
            
            logger.info(f"Face swap completed: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Face swap error: {e}", exc_info=True)
            raise

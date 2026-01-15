# Fotor API face swapping service (REUSABLE)
import http.client
import json
import base64
import logging
from pathlib import Path
from config import settings
from utils.profiler import profile
import asyncio
import aiofiles
import base64
import aiohttp
from concurrent.futures import ThreadPoolExecutor
logger = logging.getLogger(__name__)


class FaceSwapService:
    
    API_HOST = "api-b.fotor.com"
    POLL_INTERVAL = 5  # seconds
    MAX_RETRIES = 30  # 150 seconds total timeout
    _executor = ThreadPoolExecutor(max_workers=4)
    @staticmethod
    async def _to_base64(file_path: str) -> str:
        """Convert image to base64 - runs in thread pool to avoid blocking"""
        import asyncio
        
        def _sync_encode():
            with open(file_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
                ext = "jpeg" if file_path.endswith('.jpg') else Path(file_path).suffix[1:]
                return f"data:image/{ext};base64,{encoded}"
        
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
        """Swap face using Fotor API - fully async"""

        
        try:
            logger.info(f"🚀 swap_face ENTERED for {character_crop_path}")  
            user_img_b64, template_img_b64 = await asyncio.gather(FaceSwapService._to_base64(child_photo_path),
                                                                  FaceSwapService._to_base64(character_crop_path))
            payload = { 
                "userImageUrl": user_img_b64,
                "templateImageUrl": template_img_b64
            }
            
            headers = {
                'Authorization': f'Bearer {settings.FACESWAPPING_API}',
                'Content-Type': 'application/json'
            }
        
            # Submit task
            async with session.post(
                f"https://{FaceSwapService.API_HOST}/v1/aiart/faceswap",
                json=payload,
                headers=headers
            ) as resp:
                response = await resp.json()
            
            if 'data' not in response or 'taskId' not in response['data']:
                raise ValueError(f"Invalid API response: {response}")
            
            task_id = response['data']['taskId']
            logger.info(f"Face swap task created: {task_id}")
            
            # Poll for completion
            for attempt in range(FaceSwapService.MAX_RETRIES):
                await asyncio.sleep(FaceSwapService.POLL_INTERVAL)
                
                async with session.get(
                    f"https://{FaceSwapService.API_HOST}/v1/aiart/tasks/{task_id}",
                    headers={'Authorization': f'Bearer {settings.FACESWAPPING_API}'}
                ) as resp:
                    result = await resp.json()
                
                status = result.get('data', {}).get('status')
                
                if status == 1:  # Completed
                    result_url = result['data']['resultUrl']
                    logger.info(f"Face swap completed: {task_id}")
                    print("result url is", result_url)
                    
                    # Download result
                    output_path = Path(output_dir) / f"swapped_{task_id}.jpg"
                    async with session.get(result_url, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }) as img_resp:
                        img_data = await img_resp.read()
                    
                    async with aiofiles.open(output_path , "wb") as f :
                        await f.write(img_data)
                    
                    return str(output_path)
                
                elif status == -1:  # Failed
                    error_msg = result.get('data', {}).get('message', 'Unknown error')
                    raise ValueError(f"Face swap failed: {error_msg}")
                
                logger.debug(f"Face swap in progress (attempt {attempt + 1}/{FaceSwapService.MAX_RETRIES})")
            
            raise TimeoutError("Face swap timed out after 150 seconds")
            
        except Exception as e:
            logger.error(f"Face swap error: {e}", exc_info=True)
            raise

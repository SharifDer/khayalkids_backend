# Main preview generation orchestration
import logging
import os
from pathlib import Path
import numpy as np 
from deepface import DeepFace  
from repositories.preview_repo import PreviewRepository
from repositories.book_repo import BookRepository
from services.pptx_service import PPTXService
from services.faceswap_service import FaceSwapService
from services.face_detection_service import FaceDetectionService
from config import settings
from utils.profiler import save_timings
from typing import Optional, List, Dict
import asyncio
import aiohttp
from services.cartoonification_service import CartoonificationService
from services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)


class PreviewGenerationService:
    
    PREVIEW_PAGES_COUNT = 4  # First 3 slides for preview

    @staticmethod
    async def _process_single_image(
        idx: int,
        img_data: Dict,
        averaged_reference: np.ndarray,
        swapped_images_dir: Path
    ) -> Optional[Dict]:
        """Process image: detect face, START swap in background (don't wait for it)"""
        try:
            logger.info(f"Processing image {idx + 1}")
            
            img_path = Path(img_data['file_path'])
            if not img_path.exists():
                return None
            
            loop = asyncio.get_event_loop()
            
            # Run PIL Image.open in executor
            def check_image_size():
                from PIL import Image
                with Image.open(img_path) as img:
                    width, height = img.size
                    return width, height
            
            width, height = await loop.run_in_executor(None, check_image_size)
            
            if width < 350 or height < 350:
                logger.info(f"⚡ Skipping small decorative image ({width}x{height})")
                return None
            
            # Detect face
            protagonist_crop = await loop.run_in_executor(
                None,
                FaceDetectionService.isolate_protagonist_face,
                img_data['file_path'],
                averaged_reference
            )
            
            if not protagonist_crop:
                logger.warning(f"No protagonist face detected in image {idx}")
                return None
            
            logger.info(f"Matched face distance: {protagonist_crop['distance']:.2f}")
            
            # Return with pending task - swap runs in background
            return {
                'slide_idx': img_data['slide_idx'],
                'shape_id': img_data['shape_id'],
                'img_path': img_data['file_path'],
                'protagonist_crop': protagonist_crop,
                'idx': idx,
                'swapped_images_dir': swapped_images_dir
            }
            
        except Exception as e:
            logger.error(f"Error processing image {idx}: {e}", exc_info=True)
            return None

    @staticmethod
    async def process_and_swap_faces(
        extracted_images: List[Dict],
        averaged_reference: np.ndarray,
        child_photo_path: str,
        swapped_images_dir: Path,
        progress_callback: Optional[callable] = None
    ) -> List[Dict]:
        """
        SHARED METHOD: Process images and swap faces
        Used by both preview and full book generation
        
        Returns: List of {slide_idx, shape_id, swapped_path}
        """
        # STEP 1: Process each image (detect protagonist)
        tasks = [
            PreviewGenerationService._process_single_image(
                idx=idx,
                img_data=img_data,
                averaged_reference=averaged_reference,
                swapped_images_dir=swapped_images_dir
            )
            for idx, img_data in enumerate(extracted_images)
        ]
        
        logger.info(f"Starting parallel processing of {len(tasks)} images")
        results = await asyncio.gather(*tasks)
        
        # Filter out None results
        valid_results = [r for r in results if r is not None]
        
        if not valid_results:
            raise ValueError("No faces could be swapped")
        
        # STEP 2: Face swap in parallel with increased timeout
        loop = asyncio.get_event_loop()
        logger.info(f"Waiting for {len(valid_results)} face swaps in parallel")
        
        # ✅ FIX: Create session with longer timeout (10 minutes)
        timeout = aiohttp.ClientTimeout(total=600, connect=60, sock_read=600)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            swap_tasks = [
                asyncio.create_task(FaceSwapService.swap_face(
                    session=session,
                    child_photo_path=str(child_photo_path),
                    character_crop_path=r['protagonist_crop']['cropped_path'],
                    output_dir=str(swapped_images_dir)
                ))
                for r in valid_results
            ]
            swap_results = await asyncio.gather(*swap_tasks)
        
        # STEP 3: Composite all images in parallel
        logger.info(f"Compositing {len(valid_results)} images in parallel")
        composite_tasks = [
            loop.run_in_executor(
                None,
                FaceDetectionService.composite_face,
                valid_results[i]['img_path'],
                swap_results[i],
                valid_results[i]['protagonist_crop']['coordinates'],
                str(valid_results[i]['swapped_images_dir'] / f"swapped_{valid_results[i]['idx']}.jpg")
            )
            for i in range(len(valid_results))
        ]
        final_paths = await asyncio.gather(*composite_tasks)
        
        # Build metadata
        image_metadata = [
            {
                'slide_idx': valid_results[i]['slide_idx'],
                'shape_id': valid_results[i]['shape_id'],
                'swapped_path': final_paths[i]
            }
            for i in range(len(valid_results))
        ]
        
        logger.info(f"Face swapping complete: {len(image_metadata)} images")
        
        # Call progress callback if provided
        if progress_callback:
            await progress_callback(len(image_metadata))
        
        return image_metadata


    @staticmethod
    async def generate_preview(
        preview_id: int,
        preview_token: str,
        book_id: int,
        child_name: str,
        photo_path: str
    ):
        """
        Preview generation workflow with multi-reference face matching
        """
        try:
            logger.info(f"Starting preview generation for token: {preview_token}")
            
            # Create preview directory
            preview_dir = Path(settings.PREVIEWS_DIR) / preview_token
            preview_dir.mkdir(parents=True, exist_ok=True)
            
            # Get book details
            book = await BookRepository.get_by_id(book_id)
            if not book:
                raise ValueError(f"Book {book_id} not found")
            
            hero_name = book.hero_name
            
            # Parse reference paths
            reference_paths = BookRepository.parse_reference_paths(book)
            
            if not reference_paths:
                raise FileNotFoundError(f"No reference images configured for book {book_id}")
            
            valid_references = [p for p in reference_paths if p.exists()]
            
            if not valid_references:
                raise FileNotFoundError(
                    f"No reference images found. Configured: {reference_paths}"
                )
            
            logger.info(f"Using {len(valid_references)} reference images for matching")
            
            # Template paths
            template_pptx = Path(settings.TEMPLATES_DIR) / f"story_{book_id}" / "story.pptx"
            if not template_pptx.exists():
                raise FileNotFoundError(f"Template not found: {template_pptx}")
            
            # Child photo path
            full_photo_path = photo_path
            cartoon_photo_path = preview_dir / "cartoon_photo.jpg"
            await asyncio.get_event_loop().run_in_executor(
                None,
                CartoonificationService.cartoonify_photo,
                full_photo_path,
                str(cartoon_photo_path)
            )
            logger.info(f"Photo cartoonified: {cartoon_photo_path}")
            # STEP 1: Copy template and customize text
            customized_pptx = preview_dir / "customized.pptx"
            PPTXService.replace_text_in_pptx(
                pptx_path=str(template_pptx),
                replacements={hero_name: child_name},
                output_path=str(customized_pptx)
            )
            
            logger.info(f"Text customization complete: {hero_name} → {child_name}")
            
            # STEP 2: Extract images from first 3 slides
            extracted_dir = preview_dir / "extracted"
            extracted_images = PPTXService.extract_images_from_slides(
                pptx_path=str(customized_pptx),
                output_dir=str(extracted_dir),
                max_slides=PreviewGenerationService.PREVIEW_PAGES_COUNT
            )
            
            if not extracted_images:
                raise ValueError("No images extracted from template")
            
            logger.info(f"Extracted {len(extracted_images)} images")
            
            # STEP 3: Load reference embeddings
            reference_embeddings = []
            for ref_path in valid_references:
                try:
                    ref_data = DeepFace.represent(
                        img_path=str(ref_path),
                        model_name='Facenet',
                        enforce_detection=False
                    )
                    if ref_data:
                        reference_embeddings.append(np.array(ref_data[0]['embedding']))
                        logger.info(f"✅ Loaded reference: {ref_path.name}")
                except Exception as e:
                    logger.warning(f"Failed to load reference {ref_path}: {e}")
            
            if not reference_embeddings:
                raise ValueError("No valid reference images")
            
            averaged_reference = np.mean(reference_embeddings, axis=0)
            logger.info(f"⚡ Cached {len(reference_embeddings)} reference embeddings")
            
            # STEP 4: Process and swap faces (SHARED METHOD)
            swapped_images_dir = preview_dir / "swapped"
            swapped_images_dir.mkdir(exist_ok=True)
            
            image_metadata = await PreviewGenerationService.process_and_swap_faces(
                extracted_images=extracted_images,
                averaged_reference=averaged_reference,
                child_photo_path=str(cartoon_photo_path), 
                swapped_images_dir=swapped_images_dir
            )

            
            # STEP 5: Replace swapped images back into PPTX
            PPTXService.replace_images_in_pptx(
                pptx_path=str(customized_pptx),
                image_metadata=image_metadata,
                output_path=str(customized_pptx)
            )
            
            logger.info("Images replaced in PPTX")
            
            # STEP 6: Convert to slide images
            slides_dir = preview_dir / "slides"
            slide_images = PPTXService.convert_slides_to_images(
                pptx_path=str(customized_pptx),
                output_dir=str(slides_dir),
                max_slides=PreviewGenerationService.PREVIEW_PAGES_COUNT
            )
            
            # Build URLs
            swapped_image_urls = []
            for slide_image_path in slide_images:
                url = f"/{slide_image_path.replace(os.sep, '/')}"
                swapped_image_urls.append(url)
            
            logger.info(f"Generated {len(swapped_image_urls)} preview slide images")
            
            # Update database
            await PreviewRepository.update_status(
                preview_id=preview_id,
                status="completed",
                swapped_images_paths=swapped_image_urls,
                cartoon_photo_path=str(cartoon_photo_path)
            )
            await WhatsAppService.send_notifications_for_preview(preview_token, book_id)
            
            logger.info(f"Preview generation completed: {preview_token}")
            save_timings(preview_token=preview_token)
            
        except Exception as e:
            logger.error(f"Preview generation failed: {e}", exc_info=True)
            
            await PreviewRepository.update_status(
                preview_id=preview_id,
                status="failed",
                error_message=str(e)
            )
            save_timings(preview_token=preview_token)

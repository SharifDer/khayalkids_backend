# Full book generation orchestration - REUSES preview service
import logging
import os
import shutil
from pathlib import Path
import numpy as np
from deepface import DeepFace

from repositories.generated_book_repo import GeneratedBookRepository
from repositories.preview_repo import PreviewRepository
from repositories.book_repo import BookRepository
from services.preview_generation_service import PreviewGenerationService
from services.pptx_service import PPTXService
from config import settings

logger = logging.getLogger(__name__)


class FullBookGenerationService:
    
    @staticmethod
    async def generate_full_book(
        order_id: int,
        preview_token: str,
        child_name: str
    ):
        """
        Generate complete personalized book
        Reuses preview's first 3 swapped images + processes remaining slides
        """
        try:
            logger.info(f"Starting full book generation for order {order_id}")
            
            await GeneratedBookRepository.mark_processing_started(order_id)
            
            # STEP 1: Fetch preview and book data
            preview = await PreviewRepository.get_by_token(preview_token)
            if not preview or preview['preview_status'] != 'completed':
                raise ValueError(f"Preview not ready: {preview_token}")
            
            book = await BookRepository.get_by_id(preview['book_id'])
            if not book:
                raise ValueError(f"Book not found: {preview['book_id']}")
            
            hero_name = book.hero_name
            
            # STEP 2: Setup output directory
            output_dir = Path(settings.GENERATED_DIR) / str(order_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            swapped_images_dir = output_dir / "swapped"
            swapped_images_dir.mkdir(exist_ok=True)
            
            # STEP 3: Copy first 3 swapped images from preview
            logger.info("Copying first 3 swapped images from preview")
            
            preview_swapped_dir = Path(settings.PREVIEWS_DIR) / preview_token / "swapped"
            all_metadata = []
            
            if preview_swapped_dir.exists():
                swapped_files = sorted(preview_swapped_dir.glob("swapped_*.jpg"))
                
                for swapped_file in swapped_files:
                    # Extract slide index from filename
                    dest_path = swapped_images_dir / swapped_file.name
                    shutil.copy2(swapped_file, dest_path)
                    
                    # Parse slide_idx from preview's extracted images
                    # We'll rebuild metadata after processing all slides
                
                logger.info(f"Copied {len(swapped_files)} swapped images from preview")
            
            # STEP 4: Process ALL slides (including first 3 for metadata consistency)
            template_pptx = Path(settings.TEMPLATES_DIR) / f"story_{book.id}" / "story.pptx"
            if not template_pptx.exists():
                raise FileNotFoundError(f"Template not found: {template_pptx}")
            
            # Customize text
            customized_pptx = output_dir / "final_book.pptx"
            PPTXService.replace_text_in_pptx(
                pptx_path=str(template_pptx),
                replacements={hero_name: child_name},
                output_path=str(customized_pptx)
            )
            
            logger.info(f"Text customization complete")
            
            # Extract ALL images
            extracted_dir = output_dir / "extracted"
            extracted_images = PPTXService.extract_images_from_slides(
                pptx_path=str(customized_pptx),
                output_dir=str(extracted_dir),
                max_slides=None  # ALL slides
            )
            
            logger.info(f"Extracted {len(extracted_images)} images from all slides")
            
            # STEP 5: Load reference embeddings
            reference_paths = BookRepository.parse_reference_paths(book)
            valid_references = [p for p in reference_paths if p.exists()]
            
            if not valid_references:
                raise FileNotFoundError("No reference images found")
            
            reference_embeddings = []
            for ref_path in valid_references:
                try:
                    ref_data = DeepFace.represent(
                        img_path=str(ref_path),
                        model_name='Facenet512',
                        enforce_detection=False
                    )
                    if ref_data:
                        reference_embeddings.append(np.array(ref_data[0]['embedding']))
                except Exception as e:
                    logger.warning(f"Failed to load reference {ref_path}: {e}")
            
            if not reference_embeddings:
                raise ValueError("No valid reference images")
            
            # averaged_reference = np.mean(reference_embeddings, axis=0)
            # averaged_reference = averaged_reference / np.linalg.norm(averaged_reference)
            normalized_refs = [emb / np.linalg.norm(emb) for emb in reference_embeddings]
            
            # STEP 6: Process and swap faces using SHARED METHOD
            child_photo_path = preview['cartoon_photo_path']
            
            # Progress callback
            async def update_progress(completed_count):
                await GeneratedBookRepository.update_progress(
                    order_id=order_id,
                    characters_completed=completed_count,
                    estimated_time_minutes=max(1, (len(extracted_images) - completed_count) // 3)
                )
            
            image_metadata = await PreviewGenerationService.process_and_swap_faces(
                extracted_images=extracted_images,
                averaged_reference=normalized_refs,
                child_photo_path=child_photo_path,
                swapped_images_dir=swapped_images_dir,
                progress_callback=update_progress
            )
            
            # STEP 7: Replace images in PPTX
            logger.info("Replacing all swapped images in PPTX")
            PPTXService.replace_images_in_pptx(
                pptx_path=str(customized_pptx),
                image_metadata=image_metadata,
                output_path=str(customized_pptx)
            )
            
            # STEP 8: Convert to PDF
            logger.info("Converting PPTX to PDF")
            final_pdf_path = PPTXService.convert_pptx_to_pdf(
                pptx_path=str(customized_pptx),
                output_dir=str(output_dir)
            )
            
            # STEP 9: Update database
            swapped_image_urls = [
                f"/{img['swapped_path'].replace(os.sep, '/')}"
                for img in image_metadata
            ]
            
            await GeneratedBookRepository.update_final_paths(
                order_id=order_id,
                final_pptx_path=str(customized_pptx).replace(os.sep, '/'),
                final_pdf_path=final_pdf_path.replace(os.sep, '/'),
                swapped_images_paths=swapped_image_urls
            )
            
            logger.info(f"Full book generation completed for order {order_id}")
            
        except Exception as e:
            logger.error(f"Full book generation failed: {e}", exc_info=True)
            
            await GeneratedBookRepository.update_status(
                order_id=order_id,
                status="failed",
                error_message=str(e)
            )

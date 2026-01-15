# In services/face_detection_service.py

from deepface import DeepFace
import cv2
import numpy as np
import logging
from pathlib import Path
from typing import Optional, Dict
from PIL import Image, ImageFilter
from utils.profiler import profile

logger = logging.getLogger(__name__)


class FaceDetectionService:
    
    PADDING_PERCENT = 0.30
    SIMILARITY_THRESHOLD = 8.0
    
    @staticmethod
    @profile
    def isolate_protagonist_face(
        full_image_path: str,
        averaged_reference: np.ndarray  
    ) -> Optional[Dict]:
        """
        Detect protagonist using cached averaged embedding
        """
        try:
            # Load full image
            full_image = cv2.imread(full_image_path)
            
            if full_image is None:
                logger.error(f"Failed to load image: {full_image_path}")
                return None
            
            logger.info(f"Full image shape: {full_image.shape}")
            
            # Detect faces
            faces = DeepFace.extract_faces(
                img_path=full_image_path,
                detector_backend='retinaface',
                 enforce_detection=False 
            )
            
            logger.info(f"Number of faces detected: {len(faces)}")
            
            if not faces:
                logger.warning(f"No faces detected in {full_image_path}")
                return None
            
            # ✨ OPTIMIZATION 1: Single face = skip comparison
            if len(faces) == 1:
                logger.info("⚡ Single face detected - skipping comparison")
                best_match_idx = 0
                best_distance = 0.0
            else:
                # ✨ OPTIMIZATION 2: Multiple faces - use cached embedding
                logger.info(f"Multiple faces ({len(faces)}) - comparing against cached embedding")
                
                temp_dir = Path(full_image_path).parent / "temp_crops"
                temp_dir.mkdir(exist_ok=True)
                
                best_match_idx = None
                best_distance = float('inf')
                
                for idx, face in enumerate(faces):
                    area = face['facial_area']
                    x, y, w, h = area['x'], area['y'], area['w'], area['h']
                    
                    # Crop face region
                    face_crop = full_image[y:y+h, x:x+w]
                    
                    # Save crop to disk for DeepFace
                    temp_crop_path = temp_dir / f"face_{idx}.jpg"
                    cv2.imwrite(str(temp_crop_path), face_crop)
                    
                    logger.info(f"Face {idx}: crop shape {face_crop.shape}, area ({x},{y},{w},{h})")
                    
                    # Get embedding
                    try:
                        face_data = DeepFace.represent(
                            img_path=str(temp_crop_path),
                            model_name='Facenet',
                            enforce_detection=False
                        )
                        
                        if face_data:
                            encoding = np.array(face_data[0]['embedding'])
                            distance = np.linalg.norm(averaged_reference - encoding)
                            
                            logger.info(f"Face {idx} distance: {distance:.2f}")
                            
                            if distance < best_distance:
                                best_distance = distance
                                best_match_idx = idx
                                
                    except Exception as e:
                        logger.warning(f"Failed to process face {idx}: {e}")
                        continue
                
                # Clean up temp files
                import shutil
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                
                if best_distance > FaceDetectionService.SIMILARITY_THRESHOLD or best_match_idx is None:
                    logger.warning(f"No protagonist match found (best distance: {best_distance:.2f})")
                    return None
            
            logger.info(f"✅ Best match: Face {best_match_idx} with distance {best_distance:.2f}")
            
            # Get best match location
            area = faces[best_match_idx]['facial_area']
            left, top = area['x'], area['y']
            right, bottom = left + area['w'], top + area['h']
            
            # Add padding
            height, width = full_image.shape[:2]
            face_width = right - left
            face_height = bottom - top
            
            padding_w = int(face_width * FaceDetectionService.PADDING_PERCENT)
            padding_h = int(face_height * FaceDetectionService.PADDING_PERCENT)
            
            crop_top = max(0, top - padding_h)
            crop_bottom = min(height, bottom + padding_h)
            crop_left = max(0, left - padding_w)
            crop_right = min(width, right + padding_w)
            
            cropped_face = full_image[crop_top:crop_bottom, crop_left:crop_right]
            
            output_path = Path(full_image_path).parent / f"crop_{Path(full_image_path).name}"
            cv2.imwrite(str(output_path), cropped_face)
            
            logger.info(f"Protagonist face isolated: {output_path}")
            
            return {
                'cropped_path': str(output_path),
                'distance': best_distance,
                'num_references': -1,  # Indicates cached embedding was used
                'coordinates': {
                    'top': crop_top,
                    'bottom': crop_bottom,
                    'left': crop_left,
                    'right': crop_right
                }
            }
            
        except Exception as e:
            logger.error(f"Face isolation error: {e}", exc_info=True)
            return None
    
    
    @staticmethod
    @profile
    def composite_face(
        original_image_path: str,
        swapped_face_path: str,
        face_coordinates: Dict,
        output_path: str
    ) -> str:
        """
        Composite swapped face back into original image
        """
        try:
            original = Image.open(original_image_path).convert('RGB')
            swapped_face = Image.open(swapped_face_path).convert('RGB')
            
            crop_width = face_coordinates['right'] - face_coordinates['left']
            crop_height = face_coordinates['bottom'] - face_coordinates['top']
            swapped_face = swapped_face.resize((crop_width, crop_height), Image.LANCZOS)
            
            mask = Image.new('L', (crop_width, crop_height), 255)
            mask = mask.filter(ImageFilter.GaussianBlur(radius=8))
            
            original.paste(
                swapped_face,
                (face_coordinates['left'], face_coordinates['top']),
                mask
            )
            
            original.save(output_path, 'JPEG', quality=95)
            
            logger.info(f"Face composited: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Compositing error: {e}", exc_info=True)
            raise

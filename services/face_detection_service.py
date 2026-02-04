# In services/face_detection_service.py

from deepface import DeepFace
import cv2
import numpy as np
import logging
from pathlib import Path
from typing import Optional, Dict
from PIL import Image, ImageFilter
from utils.profiler import profile
from ultralytics import YOLO

logger = logging.getLogger(__name__)


class FaceDetectionService:
    
    PADDING_PERCENT = 0.30
    SIMILARITY_THRESHOLD = 8.0
    _yolo_model = None 

    @staticmethod
    def _get_yolo_model():
        """Lazy load and cache YOLO model"""
        if FaceDetectionService._yolo_model is None:
            FaceDetectionService._yolo_model = YOLO('yolov8n-seg.pt')
            logger.info("✅ YOLOv8n-seg model loaded and cached")
        return FaceDetectionService._yolo_model
    

    @staticmethod
    @profile
    def detect_person_regions(image_path: str) -> list:
        """
        Detect all person regions in image using YOLO
        Returns list of bounding boxes with padding
        """
        try:
            import cv2
            import numpy as np
            
            model = FaceDetectionService._get_yolo_model()
            
            # Load image to get dimensions
            image = cv2.imread(image_path)
            height, width = image.shape[:2]
            
            # Run inference
            results = model(image_path, verbose=False)
            
            if results[0].boxes is None or len(results[0].boxes) == 0:
                logger.warning(f"No objects detected in {image_path}")
                return []
            
            boxes = results[0].boxes.xyxy.cpu().numpy()
            classes = results[0].boxes.cls.cpu().numpy()
            
            # Filter for person class only (class ID = 0)
            person_indices = np.where(classes == 0)[0]
            
            if len(person_indices) == 0:
                logger.warning(f"No people detected in {image_path}")
                return []
            
            logger.info(f"Found {len(person_indices)} person(s)")
            
            # Apply 2px padding
            pad = 2
            person_regions = []
            
            for idx in person_indices:
                box = boxes[idx].astype(int)
                x1, y1, x2, y2 = box
                
                # Apply padding within bounds
                x1_padded = max(0, x1 - pad)
                y1_padded = max(0, y1 - pad)
                x2_padded = min(width, x2 + pad)
                y2_padded = min(height, y2 + pad)
                
                person_regions.append({
                    'bbox': (x1_padded, y1_padded, x2_padded, y2_padded),
                    'index': len(person_regions)
                })
            
            return person_regions
            
        except Exception as e:
            logger.error(f"YOLO detection error: {e}", exc_info=True)
            return []
    
    @staticmethod
    @profile
    def isolate_protagonist_face(
        full_image_path: str,
        averaged_reference: np.ndarray  
    ) -> Optional[Dict]:
        """
        Detect protagonist using YOLO + face detection with cached averaged embedding
        """
        try:
            # Load full image
            full_image = cv2.imread(full_image_path)
            
            if full_image is None:
                logger.error(f"Failed to load image: {full_image_path}")
                return None
            
            logger.info(f"Full image shape: {full_image.shape}")
            
            # STEP 1: Detect person regions with YOLO
            person_regions = FaceDetectionService.detect_person_regions(full_image_path)
            
            if not person_regions:
                logger.warning(f"No people detected in {full_image_path}")
                return None
            
            # STEP 2: Single person = skip comparison
            if len(person_regions) == 1:
                logger.info("⚡ Single person detected - skipping comparison")
                best_person_bbox = person_regions[0]['bbox']
                best_distance = 0.0
            else:
                # STEP 3: Multiple people - find protagonist by face matching
                logger.info(f"Multiple people ({len(person_regions)}) - comparing faces")
                
                temp_dir = Path(full_image_path).parent / "temp_crops"
                temp_dir.mkdir(exist_ok=True)
                
                best_match_idx = None
                best_distance = float('inf')
                best_person_bbox = None
                
                for person_data in person_regions:
                    bbox = person_data['bbox']
                    idx = person_data['index']
                    x1, y1, x2, y2 = bbox
                    
                    # Crop person region
                    person_crop = full_image[y1:y2, x1:x2]
                    
                    # Save crop for face detection
                    person_crop_path = temp_dir / f"person_{idx}.jpg"
                    cv2.imwrite(str(person_crop_path), person_crop)
                    
                    # Detect face within person crop
                    try:
                        faces = DeepFace.extract_faces(
                            img_path=str(person_crop_path),
                            detector_backend='retinaface',
                            enforce_detection=False
                        )
                        
                        if not faces:
                            logger.info(f"No face in person {idx}")
                            continue
                        
                        # Get face embedding from crop
                        face_data = DeepFace.represent(
                            img_path=str(person_crop_path),
                            model_name='Facenet',
                            enforce_detection=False
                        )
                        
                        if face_data:
                            encoding = np.array(face_data[0]['embedding'])
                            distance = np.linalg.norm(averaged_reference - encoding)
                            
                            logger.info(f"Person {idx} face distance: {distance:.2f}")
                            
                            if distance < best_distance:
                                best_distance = distance
                                best_match_idx = idx
                                best_person_bbox = bbox
                                
                    except Exception as e:
                        logger.warning(f"Failed to process person {idx}: {e}")
                        continue
                
                # Clean up temp files
                import shutil
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                
                if best_distance > FaceDetectionService.SIMILARITY_THRESHOLD or best_person_bbox is None:
                    logger.warning(f"No protagonist match found (best distance: {best_distance:.2f})")
                    return None
                
                logger.info(f"✅ Best match: Person {best_match_idx} with distance {best_distance:.2f}")
            
            # STEP 4: Crop protagonist's full body region (from YOLO bbox)
            x1, y1, x2, y2 = best_person_bbox
            cropped_character = full_image[y1:y2, x1:x2]
            
            output_path = Path(full_image_path).parent / f"crop_{Path(full_image_path).name}"
            cv2.imwrite(str(output_path), cropped_character)
            
            logger.info(f"Protagonist character isolated: {output_path}")
            
            return {
                'cropped_path': str(output_path),
                'distance': best_distance,
                'num_references': -1,
                'coordinates': {
                    'top': y1,
                    'bottom': y2,
                    'left': x1,
                    'right': x2
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

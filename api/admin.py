from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from schemas.requests import CreateBookRequest, UpdateBookRequest
import json
from repositories.book_repo import BookRepository
import os
import shutil
from pathlib import Path
from typing import Optional
from config import settings

import logging

logger = logging.getLogger(__name__)

router = APIRouter()



@router.post("/admin/create_book")
async def create_book(
    book: CreateBookRequest = Depends(),  
    template_file: UploadFile = File(...),
    cover_image: UploadFile = File(...),
    character_reference_images: list[UploadFile] = File(...), 
    preview_images: list[UploadFile] = File(...)
):
    
    book_id = await BookRepository.create(book.dict())

    # files paths
    base_path = f"{settings.TEMPLATES_DIR}/story_{book_id}"
    previews_path = f"{base_path}/previews"
    os.makedirs(previews_path, exist_ok=True)

    # حفظ القالب
    template_path = f"{base_path}/story.pptx"
    with open(template_path, "wb") as f:
        shutil.copyfileobj(template_file.file, f)

    # حفظ الغلاف
    cover_path = f"{base_path}/cover.jpg"
    with open(cover_path, "wb") as f:
        shutil.copyfileobj(cover_image.file, f)

    # ✨ CHANGED: حفظ صور المرجع للشخصية (multiple files)
    reference_paths = []
    for i, ref_image in enumerate(character_reference_images, start=1):
        reference_path = f"{base_path}/reference_{i}.png"
        with open(reference_path, "wb") as f:
            shutil.copyfileobj(ref_image.file, f)
        reference_paths.append(reference_path)
    
    # Log how many references were saved
    logger.info(f"Saved {len(reference_paths)} reference images for book {book_id}")

    # حفظ المعاينات
    preview_paths = []
    for i, image in enumerate(preview_images, start=1):
        path = f"{previews_path}/page_{i}.jpg"
        with open(path, "wb") as f:
            shutil.copyfileobj(image.file, f)
        preview_paths.append(f"{base_path}/previews/page_{i}.jpg")

    # ✨ CHANGED: تحديث المسارات (pass list of references)
    await BookRepository.update_paths(
        book_id=book_id,
        template_path=template_path,
        cover_image_path=cover_path,
        character_reference_image_urls=reference_paths,  # ✨ Now a list
        preview_images=preview_paths
    )

    return {
        "book_id": book_id,
        "message": f"Book created with {len(reference_paths)} reference images"
    }


@router.patch("/admin/books/{book_id}")
async def update_book(
    book_id: int,
    book: UpdateBookRequest = Depends(),
    template_file: Optional[UploadFile] = File(None),
    cover_image: Optional[UploadFile] = File(None),
    character_reference_images: Optional[list[UploadFile]] = File(None),
    preview_images: Optional[list[UploadFile]] = File(None)
):
    # Check book exists
    existing = await BookRepository.get_by_id(book_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Book not found")
    
    base_path = f"{settings.TEMPLATES_DIR}/story_{book_id}"
    previews_path = f"{base_path}/previews"
    
    updates = {}
    
    # Handle metadata
    metadata = book.dict(exclude_none=True)
    if metadata:
        updates.update(metadata)
    
    # Handle template file
    if template_file:
        template_path = f"{base_path}/story.pptx"
        with open(template_path, "wb") as f:
            shutil.copyfileobj(template_file.file, f)
        updates['template_path'] = template_path
    
    # Handle cover image
    if cover_image:
        cover_path = f"{base_path}/cover.jpg"
        with open(cover_path, "wb") as f:
            shutil.copyfileobj(cover_image.file, f)
        updates['cover_image_path'] = cover_path
    
    # Handle character references
    if character_reference_images:
        # Delete old references
        for old_file in Path(base_path).glob("reference_*.png"):
            old_file.unlink()
        
        # Save new ones
        reference_paths = []
        for i, ref_image in enumerate(character_reference_images, start=1):
            reference_path = f"{base_path}/reference_{i}.png"
            with open(reference_path, "wb") as f:
                shutil.copyfileobj(ref_image.file, f)
            reference_paths.append(reference_path)
        
        updates['character_reference_image_url'] = json.dumps(reference_paths)
    
    # Handle preview images
    if preview_images:
        # Delete old previews
        if os.path.exists(previews_path):
            shutil.rmtree(previews_path)
        os.makedirs(previews_path, exist_ok=True)
        
        # Save new ones
        preview_paths = []
        for i, image in enumerate(preview_images, start=1):
            path = f"{previews_path}/page_{i}.jpg"
            with open(path, "wb") as f:
                shutil.copyfileobj(image.file, f)
            preview_paths.append(f"{base_path}/previews/page_{i}.jpg")
        
        updates['preview_images'] = json.dumps(preview_paths)
    
    # Update database
    if updates:
        await BookRepository.update(book_id, updates)
    
    return {"message": f"Book {book_id} updated", "updated_fields": list(updates.keys())}

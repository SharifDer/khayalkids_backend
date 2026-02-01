from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from schemas.requests import CreateBookRequest, UpdateBookRequest
import json
from repositories.book_repo import BookRepository
import os
import shutil
from pathlib import Path
from config import settings
from typing import Annotated, Any
from pydantic import BeforeValidator
from pydantic.json_schema import SkipJsonSchema
from utils.file_utils import compress_image
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
    cover_compressed = compress_image(cover_image, max_width=1000)
    with open(cover_path, "wb") as f:
         f.write(cover_compressed)

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
        preview_compressed = compress_image(image, max_width=1000)
        with open(path, "wb") as f:
            f.write(preview_compressed)
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



def empty_str_to_none(v: Any) -> Any:
    if v == "" or v == ["string"] or (isinstance(v, list) and len(v) == 1 and v[0] == "string"):
        return None
    return v

@router.patch("/admin/books/{book_id}")
async def update_book(
    book_id: int,
    book: UpdateBookRequest = Depends(),
    template_file: Annotated[UploadFile | SkipJsonSchema[None], BeforeValidator(empty_str_to_none), File()] = None,
    cover_image: Annotated[UploadFile | SkipJsonSchema[None], BeforeValidator(empty_str_to_none), File()] = None,
    character_reference_images: Annotated[list[UploadFile] | SkipJsonSchema[None], BeforeValidator(empty_str_to_none), File()] = None,
    preview_images: Annotated[list[UploadFile] | SkipJsonSchema[None], BeforeValidator(empty_str_to_none), File()] = None
):
    """
    UPDATES (overwrites value in DB):
    title, description, age_range, gender, price, hero_name

    Only if provided in request

    REPLACES (deletes old files + saves new):
    character_reference_images: Deletes ALL reference_*.png, creates new reference_1.png, reference_2.png, etc.

    preview_images: Deletes entire previews/ folder, creates new page_1.jpg, page_2.jpg, etc.

    OVERWRITES (replaces file content, same filename):
    template_file: Overwrites story.pptx

    cover_image: Overwrites cover.jpg
    """
    print(f"=== DEBUG UPDATE BOOK {book_id} ===")
    print(f"cover_image: {cover_image}")
    print(f"cover_image type: {type(cover_image)}")
    if cover_image:
        print(f"cover_image.filename: {cover_image.filename}")
        print(f"cover_image.size: {cover_image.size}")
    print("================================")
    existing = await BookRepository.get_by_id(book_id)
    if  existing:
        raise HTTPException(status_code=404, detail="Book not found")
    
    base_path = f"{settings.TEMPLATES_DIR}/story_{book_id}"
    previews_path = f"{base_path}/previews"
    updates = {}
    
    # Metadata
    metadata = book.dict(exclude_none=True)
    if metadata:
        updates.update(metadata)
    
    # Template
    if template_file:
        template_path = f"{base_path}/story.pptx"
        with open(template_path, "wb") as f:
            shutil.copyfileobj(template_file.file, f)
        updates['template_path'] = template_path
    
    # Cover
    if cover_image:
        cover_path = f"{base_path}/cover.jpg"
        cover_compressed = compress_image(cover_image, max_width=1000)
        with open(cover_path, "wb") as f:
            f.write(cover_compressed)
        updates['cover_image_path'] = cover_path
    
    # Character references
    if character_reference_images:
        for old_file in Path(base_path).glob("reference_*.png"):
            old_file.unlink()
        reference_paths = []
        for i, ref_image in enumerate(character_reference_images, start=1):
            reference_path = f"{base_path}/reference_{i}.png"
            with open(reference_path, "wb") as f:
                shutil.copyfileobj(ref_image.file, f)
            reference_paths.append(reference_path)
        updates['character_reference_image_url'] = json.dumps(reference_paths)
    
    # Preview images
    if preview_images:
        if os.path.exists(previews_path):
            for old_file in Path(previews_path).glob("*"):
                try:
                    old_file.unlink()
                except PermissionError:
                    pass
        os.makedirs(previews_path, exist_ok=True)
        
        preview_paths = []
        for i, image in enumerate(preview_images, start=1):
            path = f"{previews_path}/page_{i}.jpg"
            preview_compressed = compress_image(image, max_width=1000)
            with open(path, "wb") as f:
                f.write(preview_compressed)
            preview_paths.append(f"{base_path}/previews/page_{i}.jpg")
    
    if updates:
        await BookRepository.update(book_id, updates)
    
    return {"message": f"Book {book_id} updated", "updated_fields": list(updates.keys())}

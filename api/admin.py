from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from schemas.requests import CreateBookRequest, UpdateBookRequest
import json
from repositories.book_repo import BookRepository
from repositories.order_repo import OrderRepository
from repositories.contact_repo import ContactRepository
from repositories.generated_book_repo import GeneratedBookRepository
from schemas.responses import (
    AdminStatsResponse, StatsSummary, PreviewDetail, OrderDetail,
    GeneratedBookDetail, ContactDetail
)
from collections import Counter
from datetime import datetime, timedelta
import os
import shutil
from pathlib import Path
from config import settings
from typing import Annotated, Any, Optional
from pydantic import BeforeValidator
from pydantic.json_schema import SkipJsonSchema
from utils.file_utils import compress_image
import logging
from repositories.preview_repo import PreviewRepository
logger = logging.getLogger(__name__)

router = APIRouter()



@router.post("/admin/create_book")
async def create_book(
    admin_password : str,
    book: CreateBookRequest = Depends(),  
    template_file: UploadFile = File(...),
    cover_image: UploadFile = File(...),
    character_reference_images: list[UploadFile] = File(...), 
    preview_images: list[UploadFile] = File(...)
):
    if admin_password != settings.admin_password:
        logger.info("Non admin tried to make changes")
        raise HTTPException(status_code=404, detail="Password is wrong, please make sure you are an admin and have the right password")
    
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
    admin_password : str,
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
    if admin_password != settings.admin_password:
        logger.info("Non admin tried to make changes")
        raise HTTPException(status_code=404, detail="Password is wrong, please make sure you are an admin and have the right password")
    existing = await BookRepository.get_by_id(book_id)
    if not existing:
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



@router.get("/admin/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    admin_password: str,
    days: Optional[int] = Query(None, description="Filter data from last N days"),
    hours: Optional[int] = Query(None, description="Filter data from last N hours")
):
    """
    Get comprehensive admin statistics with optional time filters.
    
    - **admin_password**: Admin authentication password
    - **days**: Optional - Filter data from last N days
    - **hours**: Optional - Filter data from last N hours (takes precedence over days)
    """
    # Authentication
    if admin_password != settings.admin_password:
        raise HTTPException(status_code=404, detail="Please enter a correct admin password")
    
    # Calculate time filter
    since: Optional[datetime] = None
    time_filter_desc: Optional[str] = None
    
    if hours is not None:
        since = datetime.utcnow() - timedelta(hours=hours)
        time_filter_desc = f"last_{hours}_hours"
    elif days is not None:
        since = datetime.utcnow() - timedelta(days=days)
        time_filter_desc = f"last_{days}_days"
    
    # Fetch all data
    previews_data = await PreviewRepository.get_all_previews(since=since)
    orders_data = await OrderRepository.get_all_orders(since=since)
    generated_books_data = await GeneratedBookRepository.get_all_generated_books(since=since)
    contacts_data = await ContactRepository.get_all_contacts(since=since)
    
    # Convert to response models
    previews = [PreviewDetail(**preview) for preview in previews_data]
    orders = [OrderDetail(**order) for order in orders_data]
    generated_books = [GeneratedBookDetail(**book) for book in generated_books_data]
    contacts = [ContactDetail(**contact) for contact in contacts_data]
    
    # Calculate summary statistics
    previews_by_status = dict(Counter(p.preview_status for p in previews))
    orders_by_status = dict(Counter(o.order_status for o in orders))
    orders_by_payment_status = dict(Counter(o.payment_status for o in orders))
    generated_books_by_status = dict(Counter(gb.generation_status for gb in generated_books))
    
    contacts_messages_sent = sum(1 for c in contacts if c.message_sent == 1)
    contacts_messages_pending = sum(1 for c in contacts if c.message_sent == 0)
    
    summary = StatsSummary(
        total_previews=len(previews),
        previews_by_status=previews_by_status,
        total_orders=len(orders),
        orders_by_status=orders_by_status,
        orders_by_payment_status=orders_by_payment_status,
        total_generated_books=len(generated_books),
        generated_books_by_status=generated_books_by_status,
        total_contacts=len(contacts),
        contacts_messages_sent=contacts_messages_sent,
        contacts_messages_pending=contacts_messages_pending
    )
    
    return AdminStatsResponse(
        summary=summary,
        previews=previews,
        orders=orders,
        generated_books=generated_books,
        contacts=contacts,
        time_filter=time_filter_desc
    )
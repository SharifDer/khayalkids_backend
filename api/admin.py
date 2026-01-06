from fastapi import APIRouter, UploadFile, File, Depends
from schemas.requests import CreateBookRequest
from repositories.book_repo import BookRepository
import os
import shutil
from config import settings

router = APIRouter()

@router.post("/admin/books")
async def create_book(
    book: CreateBookRequest = Depends(),  
    template_file: UploadFile = File(...),
    cover_image: UploadFile = File(...),
    preview_images: list[UploadFile] = File(...)
):
    # إنشاء الكتاب (بيانات فقط)
    book_id = await BookRepository.create(book.dict())

    # مسارات الملفات
    base_path = f"{settings.TEMPLATES_DIR}/story_{book_id}"
    previews_path = f"{base_path}/previews"
    os.makedirs(previews_path, exist_ok=True)


    template_path = f"{base_path}/template.pptx"
    with open(template_path, "wb") as f:
        shutil.copyfileobj(template_file.file, f)

    # حفظ الغلاف
    cover_path = f"{base_path}/cover.jpg"
    with open(cover_path, "wb") as f:
        shutil.copyfileobj(cover_image.file, f)

    # حفظ المعاينات
    preview_paths = []
    for i, image in enumerate(preview_images, start=1):
        path = f"{previews_path}/page_{i}.jpg"
        with open(path, "wb") as f:
            shutil.copyfileobj(image.file, f)
        preview_paths.append(f"{base_path}/previews/page_{i}.jpg")

    # تحديث المسارات
    await BookRepository.update_paths(
        book_id=book_id,
        template_path=template_path,
        cover_image_path=cover_path,
        preview_images=preview_paths
    )

    return {
        "book_id": book_id,
        "message": "Book created"
    }

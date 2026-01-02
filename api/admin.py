
from fastapi import APIRouter, Form, UploadFile, File
from repositories.book_repo import BookRepository
import os
import shutil


router = APIRouter()


@router.post("/admin/books")
async def create_book(
    title: str = Form(...),
    description: str = Form(...),
    age_range: str = Form(...),
    gender: str = Form(...),
    price: float = Form(...),

    template_file: UploadFile = File(...),
    cover_image: UploadFile = File(...),
    preview_images: list[UploadFile] = File(...)
):
    #  إنشاء الكتاب في قاعدة البيانات (بدون ملفات)
    book_id = await BookRepository.create(
        type("obj", (), {
            "title": title,
            "description": description,
            "age_range": age_range,
            "gender": gender,
            "price": price
        })
    )

    #  إنشاء مجلدات القصة
    base_path = f"stories/templates/story_{book_id}"
    previews_path = f"{base_path}/previews"


    os.makedirs(previews_path, exist_ok=True)

    #  حفظ ملف القالب
    template_path = f"{base_path}/template.pptx"
    with open(template_path, "wb") as f:
        shutil.copyfileobj(template_file.file, f)

    #  حفظ صورة الغلاف
    cover_path = f"{base_path}/cover.jpg"
    with open(cover_path, "wb") as f:
        shutil.copyfileobj(cover_image.file, f)

    #  حفظ صور المعاينة
    preview_paths = []
    for index, image in enumerate(preview_images, start=1):
        image_path = f"{previews_path}/page_{index}.jpg"
        with open(image_path, "wb") as f:
            shutil.copyfileobj(image.file, f)
        preview_paths.append(f"page_{index}.jpg")

    #  تحديث المسارات في قاعدة البيانات
    await BookRepository.update_paths(
        book_id=book_id,
        template_path=template_path,
        cover_image_path=cover_path,
        preview_images=preview_paths
    )

    return {
        "book_id": book_id,
        "message": "Book created with files"
    }


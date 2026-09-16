"""واجهات المرفقات — رفع الملفات على القيود مع فحص الأمان."""
import os
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.attachment import ALLOWED_MIME_TYPES, MAX_FILE_SIZE, Attachment
from app.models.journal import JournalEntry
from app.models.user import User

router = APIRouter(prefix="/api/attachments", tags=["المرفقات"])

ATTACHMENTS_DIR = Path("/app/attachments")
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".xlsx", ".xls", ".csv"}


def _validate_file(upload: UploadFile) -> None:
    """فحص نوع وحجم الملف قبل الحفظ."""
    ext = Path(upload.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"نوع الملف غير مسموح. المسموح: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    if upload.content_type and upload.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=422, detail="نوع المحتوى غير مسموح")


@router.post("/entry/{entry_id}", status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    entry_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """رفع مرفق على قيد — يُمنع الرفع على قيد مرحَّل."""
    entry = db.get(JournalEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="القيد غير موجود")
    if entry.state == "posted":
        raise HTTPException(status_code=400, detail="لا يمكن إرفاق ملفات على قيد مرحَّل")

    _validate_file(file)

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=422, detail="حجم الملف يتجاوز 10MB")
    if len(content) == 0:
        raise HTTPException(status_code=422, detail="الملف فارغ")

    # اسم آمن فريد — يمنع تجاوز المسار
    safe_name = f"{uuid.uuid4().hex}{Path(file.filename or 'file').suffix.lower()}"
    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    stored_path = ATTACHMENTS_DIR / safe_name
    stored_path.write_bytes(content)

    attachment = Attachment(
        entry_id=entry_id,
        filename=file.filename or "file",
        stored_path=str(stored_path),
        mime_type=file.content_type or "application/octet-stream",
        file_size=len(content),
        uploaded_by=current_user.id,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return {
        "id": str(attachment.id),
        "filename": attachment.filename,
        "file_size": attachment.file_size,
        "mime_type": attachment.mime_type,
    }


@router.get("/entry/{entry_id}")
async def list_entry_attachments(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = db.get(JournalEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="القيد غير موجود")
    return [
        {
            "id": str(a.id),
            "filename": a.filename,
            "file_size": a.file_size,
            "mime_type": a.mime_type,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in entry.attachments
    ]


@router.delete("/{attachment_id}")
async def delete_attachment(
    attachment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """حذف مرفق — يُمنع على قيد مرحَّل."""
    attachment = db.get(Attachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="المرفق غير موجود")
    if attachment.entry.state == "posted":
        raise HTTPException(status_code=400, detail="لا يمكن حذف مرفق من قيد مرحَّل")

    try:
        os.remove(attachment.stored_path)
    except FileNotFoundError:
        pass

    db.delete(attachment)
    db.commit()
    return {"message": "تم حذف المرفق"}

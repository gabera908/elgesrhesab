"""أدوات مشتركة لفلاتر التقارير — فلتر المشروع (project_id) عبر مركز التكلفة."""
import uuid
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.project import Project


def resolve_project_cost_center(db: Session, project_id: Optional[uuid.UUID]) -> Optional[uuid.UUID]:
    """يحوّل project_id إلى cost_center_id لفلترة حركات القيود (MoveLine.cost_center_id).

    يرفع 404 إذا المشروع غير موجود، و422 إذا لم يكن له مركز تكلفة.
    يُعيد None إذا لم يُمرَّر project_id (بدون فلترة).
    """
    if project_id is None:
        return None
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")
    if project.cost_center_id is None:
        raise HTTPException(
            status_code=422,
            detail="هذا المشروع غير مرتبط بمركز تكلفة — اربطه أولاً من صفحة المشاريع",
        )
    return project.cost_center_id

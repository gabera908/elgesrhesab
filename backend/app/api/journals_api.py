"""واجهات الدفاتر المحاسبية."""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.journal import Journal

router = APIRouter(prefix="/api/journals", tags=["الدفاتر"])


@router.get("", response_model=List[dict])
async def list_journals(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """قائمة الدفاتر النشطة للاختيار في القيود."""
    rows = db.scalars(
        select(Journal).where(Journal.is_active == True).order_by(Journal.code)  # noqa: E712
    ).all()
    return [
        {
            "id": str(j.id),
            "code": j.code,
            "name": j.name,
            "journal_type": j.journal_type,
        }
        for j in rows
    ]

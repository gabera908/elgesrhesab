"""واجهات السنوات والفترات المالية — الإقفال."""
import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_permission
from app.database import get_db
from app.models.journal import FiscalYear
from app.models.period import Period
from app.models.user import User

router = APIRouter(prefix="/api/fiscal", tags=["السنوات والفترات"])


# ===== السنوات المالية =====
class FiscalYearCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    start_date: date
    end_date: date


class FiscalYearOut(BaseModel):
    id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    is_closed: bool

    class Config:
        from_attributes = True


@router.get("/years", response_model=List[FiscalYearOut])
async def list_years(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.scalars(select(FiscalYear).order_by(FiscalYear.start_date.desc())).all()


@router.post("/years", response_model=FiscalYearOut, status_code=201)
async def create_year(
    payload: FiscalYearCreate,
    current_user: User = Depends(require_permission("settings", "update")),
    db: Session = Depends(get_db),
):
    if payload.start_date > payload.end_date:
        raise HTTPException(status_code=422, detail="تاريخ البداية بعد النهاية")
    if db.scalar(select(FiscalYear).where(FiscalYear.name == payload.name)):
        raise HTTPException(status_code=409, detail="السنة موجودة مسبقاً")

    year = FiscalYear(**payload.model_dump())
    db.add(year)
    db.flush()

    # توليد 12 فترة شهرية تلقائياً
    from dateutil.relativedelta import relativedelta

    current = payload.start_date
    months_ar = [
        "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
        "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
    ]
    while current <= payload.end_date:
        next_month = current + relativedelta(months=1)
        period_end = min(next_month - relativedelta(days=1), payload.end_date)
        db.add(
            Period(
                fiscal_year_id=year.id,
                name=f"{months_ar[current.month - 1]} {current.year}",
                start_date=current,
                end_date=period_end,
            )
        )
        current = next_month

    db.commit()
    db.refresh(year)
    return year


@router.post("/years/{year_id}/close")
async def close_year(
    year_id: uuid.UUID,
    current_user: User = Depends(require_permission("settings", "update")),
    db: Session = Depends(get_db),
):
    """إقفال السنة المالية — يقفل كل الفترات."""
    year = db.get(FiscalYear, year_id)
    if year is None:
        raise HTTPException(status_code=404, detail="السنة غير موجودة")
    year.is_closed = True
    for period in year.periods:
        period.is_closed = True
    db.commit()
    return {"message": f"تم إقفال السنة {year.name}"}


# ===== الفترات =====
class PeriodOut(BaseModel):
    id: uuid.UUID
    fiscal_year_id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    is_closed: bool

    class Config:
        from_attributes = True


@router.get("/periods", response_model=List[PeriodOut])
async def list_periods(
    year_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Period).order_by(Period.start_date)
    if year_id:
        stmt = stmt.where(Period.fiscal_year_id == year_id)
    return db.scalars(stmt).all()


@router.post("/periods/{period_id}/close")
async def close_period(
    period_id: uuid.UUID,
    current_user: User = Depends(require_permission("settings", "update")),
    db: Session = Depends(get_db),
):
    period = db.get(Period, period_id)
    if period is None:
        raise HTTPException(status_code=404, detail="الفترة غير موجودة")
    period.is_closed = True
    db.commit()
    return {"message": f"تم إقفال فترة {period.name}"}


@router.post("/periods/{period_id}/reopen")
async def reopen_period(
    period_id: uuid.UUID,
    current_user: User = Depends(require_permission("settings", "update")),
    db: Session = Depends(get_db),
):
    """إعادة فتح فترة — للمدير فقط مع تسجيل في التدقيق."""
    period = db.get(Period, period_id)
    if period is None:
        raise HTTPException(status_code=404, detail="الفترة غير موجودة")
    if period.fiscal_year.is_closed:
        raise HTTPException(status_code=400, detail="السنة المالية مقفلة بالكامل")
    period.is_closed = False
    db.commit()
    return {"message": f"تمت إعادة فتح فترة {period.name}"}


def is_date_in_closed_period(db: Session, check_date: date) -> bool:
    """يتحقق إن كان التاريخ يقع في فترة مقفلة — يُستدعى قبل الترحيل."""
    period = db.scalar(
        select(Period)
        .where(Period.start_date <= check_date)
        .where(Period.end_date >= check_date)
        .limit(1)
    )
    if period is None:
        return False
    return period.is_closed or period.fiscal_year.is_closed

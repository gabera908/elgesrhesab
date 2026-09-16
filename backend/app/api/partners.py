"""واجهات الشركاء — عملاء/موردون/جهات مانحة."""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_permission
from app.database import get_db
from app.models.partner import PARTNER_TYPES, Partner
from app.models.user import User

router = APIRouter(prefix="/api/partners", tags=["الشركاء"])


class PartnerBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=30)
    name: str = Field(..., min_length=1, max_length=200)
    partner_type: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    commercial_register: Optional[str] = None
    notes: Optional[str] = None


class PartnerCreate(PartnerBase):
    pass


class PartnerUpdate(BaseModel):
    name: Optional[str] = None
    partner_type: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    commercial_register: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class PartnerOut(PartnerBase):
    id: uuid.UUID
    is_active: bool

    class Config:
        from_attributes = True


PARTNER_LABELS = {
    "customer": "عميل",
    "supplier": "مورد",
    "donor": "جهة مانحة",
    "employee": "موظف",
    "other": "أخرى",
}


@router.get("", response_model=List[PartnerOut])
async def list_partners(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    partner_type: Optional[str] = None,
    active_only: bool = True,
    search: Optional[str] = None,
):
    """قائمة الشركاء مع فلترة بالنوع والبحث."""
    stmt = select(Partner).order_by(Partner.code)
    if active_only:
        stmt = stmt.where(Partner.is_active == True)  # noqa: E712
    if partner_type:
        if partner_type not in PARTNER_TYPES:
            raise HTTPException(status_code=422, detail="نوع الشريك غير صالح")
        stmt = stmt.where(Partner.partner_type == partner_type)
    if search:
        stmt = stmt.where(
            (Partner.name.ilike(f"%{search}%")) | (Partner.code.ilike(f"%{search}%"))
        )
    return db.scalars(stmt).all()


@router.get("/types")
async def get_types():
    """أنواع الشركاء المتاحة."""
    return [{"value": k, "label": v} for k, v in PARTNER_LABELS.items()]


@router.post("", response_model=PartnerOut, status_code=status.HTTP_201_CREATED)
async def create_partner(
    payload: PartnerCreate,
    current_user: User = Depends(require_permission("partners", "create")),
    db: Session = Depends(get_db),
):
    if payload.partner_type not in PARTNER_TYPES:
        raise HTTPException(status_code=422, detail="نوع الشريك غير صالح")
    if db.scalar(select(Partner).where(Partner.code == payload.code)):
        raise HTTPException(status_code=409, detail="كود الشريك موجود مسبقاً")

    partner = Partner(**payload.model_dump())
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


@router.get("/{partner_id}", response_model=PartnerOut)
async def get_partner(
    partner_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    partner = db.get(Partner, partner_id)
    if partner is None:
        raise HTTPException(status_code=404, detail="الشريك غير موجود")
    return partner


@router.put("/{partner_id}", response_model=PartnerOut)
async def update_partner(
    partner_id: uuid.UUID,
    payload: PartnerUpdate,
    current_user: User = Depends(require_permission("partners", "update")),
    db: Session = Depends(get_db),
):
    partner = db.get(Partner, partner_id)
    if partner is None:
        raise HTTPException(status_code=404, detail="الشريك غير موجود")

    data = payload.model_dump(exclude_unset=True)
    if "partner_type" in data and data["partner_type"] not in PARTNER_TYPES:
        raise HTTPException(status_code=422, detail="نوع الشريك غير صالح")
    for key, value in data.items():
        setattr(partner, key, value)
    db.commit()
    db.refresh(partner)
    return partner


@router.post("/{partner_id}/deactivate")
async def deactivate_partner(
    partner_id: uuid.UUID,
    current_user: User = Depends(require_permission("partners", "delete")),
    db: Session = Depends(get_db),
):
    partner = db.get(Partner, partner_id)
    if partner is None:
        raise HTTPException(status_code=404, detail="الشريك غير موجود")
    partner.is_active = False
    db.commit()
    return {"message": "تم تعطيل الشريك"}

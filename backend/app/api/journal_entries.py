"""واجهات القيود اليومية — القيد المزدوج الصارم."""
import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_permission
from app.database import get_db
from app.models.account import Account
from app.models.journal import ENTRY_STATES, Journal, JournalEntry, MoveLine
from app.models.user import User

router = APIRouter(prefix="/api/journal-entries", tags=["القيود اليومية"])


class MoveLineIn(BaseModel):
    account_id: uuid.UUID
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    name: Optional[str] = None
    partner_id: Optional[uuid.UUID] = None
    cost_center_id: Optional[uuid.UUID] = None
    date_maturity: Optional[date] = None

    @model_validator(mode="after")
    def validate_exclusive(self):
        """لا يجتمع مدين ودائن في نفس السطر."""
        if self.debit > 0 and self.credit > 0:
            raise ValueError("لا يمكن أن يكون السطر مديناً ودائناً معاً")
        if self.debit < 0 or self.credit < 0:
            raise ValueError("لا يمكن قبول قيم سالبة")
        return self


class JournalEntryBase(BaseModel):
    journal_id: uuid.UUID
    entry_date: date
    reference: Optional[str] = None
    narration: Optional[str] = None
    lines: List[MoveLineIn] = Field(..., min_length=2)


class JournalEntryCreate(JournalEntryBase):
    @model_validator(mode="after")
    def validate_balanced(self):
        """القيد الذهبي: مجموع المدين = مجموع الدائن."""
        debit = sum(l.debit for l in self.lines)
        credit = sum(l.credit for l in self.lines)
        if debit != credit:
            raise ValueError(f"القيد غير متوازن: مدين {debit} ≠ دائن {credit}")
        if debit == 0:
            raise ValueError("القيد يجب أن يحتوي على قيمة")
        return self


class JournalEntryOut(JournalEntryBase):
    id: uuid.UUID
    entry_number: str
    state: str
    amount: Decimal
    created_at: object

    class Config:
        from_attributes = True


def _generate_entry_number(db: Session, journal: Journal, entry_date: date) -> str:
    """رقم تسلسلي فريد للقيد: {سنة}-{شهر}-{تسلسل}."""
    prefix = entry_date.strftime("%Y%m")
    count = (
        db.scalar(
            select(JournalEntry)
            .where(JournalEntry.entry_number.like(f"{prefix}%"))
            .order_by(JournalEntry.entry_number.desc())
            .limit(1)
        )
    )
    seq = 1
    if count and count.entry_number:
        try:
            seq = int(count.entry_number.split("-")[-1]) + 1
        except (IndexError, ValueError):
            seq = 1
    return f"{prefix}-{seq:04d}"


@router.get("")
async def list_entries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    journal_id: Optional[uuid.UUID] = None,
    state: Optional[str] = None,
    limit: int = 50,
):
    """استعراض القيود مع فلترة."""
    stmt = select(JournalEntry).order_by(JournalEntry.entry_date.desc())
    if from_date:
        stmt = stmt.where(JournalEntry.entry_date >= from_date)
    if to_date:
        stmt = stmt.where(JournalEntry.entry_date <= to_date)
    if journal_id:
        stmt = stmt.where(JournalEntry.journal_id == journal_id)
    if state:
        if state not in ENTRY_STATES:
            raise HTTPException(status_code=422, detail="حالة غير صالحة")
        stmt = stmt.where(JournalEntry.state == state)

    stmt = stmt.limit(min(limit, 500))
    return db.scalars(stmt).all()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_entry(
    payload: JournalEntryCreate,
    current_user: User = Depends(require_permission("journals", "create")),
    db: Session = Depends(get_db),
):
    """إنشاء قيد جديد كمسودة — التحقق من التوازن داخل معاملة."""
    journal = db.get(Journal, payload.journal_id)
    if journal is None or not journal.is_active:
        raise HTTPException(status_code=404, detail="الدفتر غير موجود")

    # التحقق من وجود الحسابات وصلاحية الترحيل
    account_ids = {l.account_id for l in payload.lines}
    accounts = {
        a.id: a for a in db.scalars(select(Account).where(Account.id.in_(account_ids)))
    }
    if len(accounts) != len(account_ids):
        raise HTTPException(status_code=422, detail="حساب غير موجود")
    for acc in accounts.values():
        if not acc.is_postable:
            raise HTTPException(
                status_code=422, detail=f"الحساب {acc.code} تجميعي ولا يقبل القيود"
            )

    total = sum(l.debit for l in payload.lines)

    entry = JournalEntry(
        entry_number=_generate_entry_number(db, journal, payload.entry_date),
        journal_id=payload.journal_id,
        entry_date=payload.entry_date,
        reference=payload.reference,
        narration=payload.narration,
        state="draft",
        amount=total,
        created_by=current_user.id,
    )
    db.add(entry)
    db.flush()

    for line in payload.lines:
        db.add(
            MoveLine(
                entry_id=entry.id,
                account_id=line.account_id,
                debit=line.debit,
                credit=line.credit,
                name=line.name,
                partner_id=line.partner_id,
                cost_center_id=line.cost_center_id,
                date_maturity=line.date_maturity,
            )
        )

    db.commit()
    db.refresh(entry)
    return entry


@router.post("/{entry_id}/submit-review")
async def submit_for_review(
    entry_id: uuid.UUID,
    current_user: User = Depends(require_permission("journals", "create")),
    db: Session = Depends(get_db),
):
    """إرسال القيد للمراجعة — مسودة → قيد المراجعة."""
    entry = db.get(JournalEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="القيد غير موجود")
    if entry.state != "draft":
        raise HTTPException(status_code=400, detail="القيد ليس مسودة")
    entry.state = "in_review"
    db.commit()
    return {"message": "تم إرسال القيد للمراجعة"}


@router.post("/{entry_id}/return-draft")
async def return_to_draft(
    entry_id: uuid.UUID,
    current_user: User = Depends(require_permission("journals", "post")),
    db: Session = Depends(get_db),
):
    """إعادة القيد للتعديل — قيد المراجعة → مسودة."""
    entry = db.get(JournalEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="القيد غير موجود")
    if entry.state != "in_review":
        raise HTTPException(status_code=400, detail="القيد ليس قيد مراجعة")
    entry.state = "draft"
    db.commit()
    return {"message": "تمت إعادة القيد كمسودة"}


@router.post("/{entry_id}/post")
async def post_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(require_permission("journals", "post")),
    db: Session = Depends(get_db),
):
    """ترحيل القيد — قفل التعديل بعد الترحيل + منع الترحيل في فترة مقفلة."""
    from datetime import datetime, timezone

    from app.api.fiscal import is_date_in_closed_period

    entry = db.get(JournalEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="القيد غير موجود")
    if entry.state == "posted":
        raise HTTPException(status_code=400, detail="القيد مرحَّل مسبقاً")
    if entry.state == "reversed":
        raise HTTPException(status_code=400, detail="القيد معكوس")
    if entry.state not in ("draft", "in_review"):
        raise HTTPException(status_code=400, detail="حالة القيد لا تسمح بالترحيل")

    # منع الترحيل في فترة مقفلة
    if is_date_in_closed_period(db, entry.entry_date):
        raise HTTPException(
            status_code=400,
            detail="لا يمكن الترحيل — التاريخ يقع في فترة مالية مقفلة",
        )

    # التحقق النهائي من التوازن داخل قاعدة البيانات
    debit = sum(l.debit for l in entry.lines)
    credit = sum(l.credit for l in entry.lines)
    if debit != credit:
        raise HTTPException(status_code=422, detail="القيد غير متوازن")

    entry.state = "posted"
    entry.posted_by = current_user.id
    entry.posted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "تم ترحيل القيد", "entry_number": entry.entry_number}


@router.post("/{entry_id}/reverse")
@router.post("/{entry_id}/cancel")
async def reverse_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(require_permission("journals", "cancel")),
    db: Session = Depends(get_db),
):
    """عكس قيد مرحَّل — إنشاء قيد عكسي بدل الحذف (لا حذف فعلي أبداً)."""
    entry = db.get(JournalEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="القيد غير موجود")
    if entry.state != "posted":
        raise HTTPException(status_code=400, detail="القيد غير مرحَّل")

    entry.state = "reversed"

    # قيد عكسي يعكس الآثار
    reversal = JournalEntry(
        entry_number=_generate_entry_number(db, entry.journal, entry.entry_date),
        journal_id=entry.journal_id,
        entry_date=entry.entry_date,
        reference=f"عكسي: {entry.entry_number}",
        narration=f"قيد عكسي لإلغاء {entry.entry_number}",
        state="posted",
        amount=entry.amount,
        created_by=current_user.id,
        posted_by=current_user.id,
        reversed_from_id=entry.id,
    )
    db.add(reversal)
    db.flush()
    for line in entry.lines:
        db.add(
            MoveLine(
                entry_id=reversal.id,
                account_id=line.account_id,
                debit=line.credit,  # عكس
                credit=line.debit,  # عكس
                name=f"عكسي: {line.name or ''}",
                cost_center_id=line.cost_center_id,
                partner_id=line.partner_id,
            )
        )
    db.commit()
    return {"message": "تم العكس بقيد عكسي", "reversal_number": reversal.entry_number}

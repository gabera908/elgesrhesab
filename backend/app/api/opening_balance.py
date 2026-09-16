"""الرصيد الافتتاحي للبنوك والصناديق — قيد افتتاحي آلي."""
import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_permission
from app.database import get_db
from app.models.account import Account
from app.models.journal import Journal, JournalEntry, MoveLine
from app.models.user import User

router = APIRouter(prefix="/api/settings/opening-balance", tags=["الرصيد الافتتاحي"])


class FundLine(BaseModel):
    """رصيد بنك/صندوق واحد."""

    account_id: uuid.UUID
    account_code: str
    account_name: str
    balance: Decimal

    @model_validator(mode="after")
    def non_negative(self):
        if self.balance < 0:
            raise ValueError("الرصيد لا يمكن أن يكون سالباً")
        return self


class OpeningBalanceRequest(BaseModel):
    as_of_date: date
    bank_journal_id: Optional[uuid.UUID] = None
    cash_journal_id: Optional[uuid.UUID] = None
    funds: List[FundLine]
    # الحساب المقابل للرصيد الافتتاحي (عادة: رأس المال / الأرباح المرحَّلة)
    offset_account_id: uuid.UUID

    @model_validator(mode="after")
    def has_journals(self):
        if not self.bank_journal_id and not self.cash_journal_id:
            raise ValueError("يجب اختيار دفتر بنكي أو نقدي واحد على الأقل")
        if not self.funds:
            raise ValueError("يجب إدخال رصيد واحد على الأقل")
        return self


class OpeningBalanceResponse(BaseModel):
    entry_number: str
    total: Decimal
    journal_id: uuid.UUID


@router.get("/funds")
async def list_funds(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """الحسابات النقدية والبنكية القابلة للرصيد الافتتاحي."""
    rows = db.scalars(
        select(Account).where(
            Account.is_active == True,  # noqa: E712
            Account.statement_section == "bs_current_asset",
            Account.is_postable == True,  # noqa: E712
        )
    ).all()
    return [
        {
            "id": str(a.id),
            "code": a.code,
            "name": a.name,
            "level": a.level,
        }
        for a in rows
    ]


@router.post("", response_model=OpeningBalanceResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=OpeningBalanceResponse, status_code=status.HTTP_201_CREATED)
async def create_opening_balance(
    payload: OpeningBalanceRequest,
    current_user: User = Depends(require_permission("settings", "update")),
    db: Session = Depends(get_db),
):
    """ينشئ قيد الرصيد الافتتاحي آلياً: مدين (الأصول النقدية) / دائن (رأس المال)."""
    total = sum(f.balance for f in payload.funds)
    if total <= 0:
        raise HTTPException(status_code=422, detail="مجموع الأرصدة يجب أن يكون موجباً")

    journal_id = payload.bank_journal_id or payload.cash_journal_id
    journal = db.get(Journal, journal_id)
    if journal is None or not journal.is_active:
        raise HTTPException(status_code=404, detail="الدفتر غير موجود")

    # التحقق من الحسابات
    fund_ids = {f.account_id for f in payload.funds}
    accounts = {
        a.id: a
        for a in db.scalars(select(Account).where(Account.id.in_(list(fund_ids))))
    }
    if len(accounts) != len(fund_ids):
        raise HTTPException(status_code=422, detail="حساب نقدي غير موجود")

    offset = db.get(Account, payload.offset_account_id)
    if offset is None:
        raise HTTPException(status_code=404, detail="حساب المقابل غير موجود")
    if not offset.is_postable:
        raise HTTPException(status_code=422, detail=f"الحساب {offset.code} تجميعي")

    # منع التكرار: قيد افتتاحي واحد لكل تاريخ
    existing = db.scalar(
        select(JournalEntry)
        .where(JournalEntry.reference == "OPENING-BALANCE")
        .where(JournalEntry.entry_date == payload.as_of_date)
        .where(JournalEntry.state == "posted")
        .limit(1)
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"يوجد قيد رصيد افتتاحي لهذا التاريخ: {existing.entry_number}",
        )

    entry = JournalEntry(
        entry_number=f"OP-{payload.as_of_date.strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}",
        journal_id=journal_id,
        entry_date=payload.as_of_date,
        reference="OPENING-BALANCE",
        narration="قيد الرصيد الافتتاحي للبنوك والصناديق",
        state="posted",
        amount=total,
        created_by=current_user.id,
        posted_by=current_user.id,
    )
    db.add(entry)
    db.flush()

    # مدين: الأرصدة النقدية
    for fund in payload.funds:
        db.add(
            MoveLine(
                entry_id=entry.id,
                account_id=fund.account_id,
                debit=fund.balance,
                credit=Decimal(0),
                name=f"رصيد افتتاحي — {fund.account_name}",
            )
        )

    # دائن: حساب المقابل
    db.add(
        MoveLine(
            entry_id=entry.id,
            account_id=offset.id,
            debit=Decimal(0),
            credit=total,
            name="رصيد افتتاحي — مقابل",
        )
    )
    db.commit()
    db.refresh(entry)

    return OpeningBalanceResponse(
        entry_number=entry.entry_number,
        total=total,
        journal_id=journal_id,
    )

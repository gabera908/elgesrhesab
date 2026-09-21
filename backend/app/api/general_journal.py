"""اليومية العامة — كل قيود الفترة مفصَّلة بسطورها (مستوحى من Advisor).

الفلاتر: فترة (from/to) · السنة المالية (fiscal_year_id) · المشروع (project_id) · الدفتر (journal_id)
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.report_filters import resolve_project_cost_center
from app.core.deps import require_permission
from app.database import get_db
from app.models.account import Account
from app.models.journal import FiscalYear, Journal, JournalEntry, MoveLine
from app.models.user import User

router = APIRouter(prefix="/api/reports/general-journal", tags=["اليومية العامة"])


class GeneralJournalLine(BaseModel):
    account_code: str
    account_name: str
    name: Optional[str]
    debit: Decimal
    credit: Decimal


class GeneralJournalEntry(BaseModel):
    entry_id: uuid.UUID
    entry_number: str
    entry_date: date
    journal_code: Optional[str]
    journal_name: Optional[str]
    reference: Optional[str]
    narration: Optional[str]
    state: str
    lines: List[GeneralJournalLine]
    total_debit: Decimal
    total_credit: Decimal
    is_balanced: bool


class GeneralJournalReport(BaseModel):
    from_date: date
    to_date: date
    fiscal_year_id: Optional[uuid.UUID]
    project_id: Optional[uuid.UUID]
    journal_id: Optional[uuid.UUID]
    entries: List[GeneralJournalEntry]
    entries_count: int
    grand_debit: Decimal
    grand_credit: Decimal
    is_balanced: bool


@router.get("", response_model=GeneralJournalReport)
@router.get("/", response_model=GeneralJournalReport)
async def general_journal(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    fiscal_year_id: Optional[uuid.UUID] = Query(None),
    project_id: Optional[uuid.UUID] = Query(None),
    journal_id: Optional[uuid.UUID] = Query(None),
    state: Optional[str] = Query(None, description="posted | draft | in_review | reversed"),
    current_user: User = Depends(require_permission("reports", "read")),
    db: Session = Depends(get_db),
):
    """اليومية العامة — القيود بسطورها مع مجاميع لكل قيد والمجموع العام.

    إذا حُدِّدت سنة مالية تُشتق الفترة من تواريخها (مثل سلوك Advisor).
    """
    # اشتقاق الفترة من السنة المالية إن وُجدت
    if fiscal_year_id is not None:
        fy = db.get(FiscalYear, fiscal_year_id)
        if fy is None:
            raise HTTPException(status_code=404, detail="السنة المالية غير موجودة")
        from_date, to_date = fy.start_date, fy.end_date
    if from_date is None or to_date is None:
        raise HTTPException(status_code=422, detail="حدِّد الفترة أو السنة المالية")
    if from_date > to_date:
        raise HTTPException(status_code=422, detail="تاريخ البدء بعد تاريخ الانتهاء")

    cc_id = resolve_project_cost_center(db, project_id)

    stmt = (
        select(JournalEntry)
        .where(JournalEntry.entry_date.between(from_date, to_date))
        .order_by(JournalEntry.entry_date, JournalEntry.entry_number)
    )
    if journal_id is not None:
        stmt = stmt.where(JournalEntry.journal_id == journal_id)
    if state:
        if state not in ("draft", "in_review", "posted", "reversed"):
            raise HTTPException(status_code=422, detail="حالة القيد غير صالحة")
        stmt = stmt.where(JournalEntry.state == state)

    entries = db.scalars(stmt).all()

    journals = {j.id: j for j in db.scalars(select(Journal)).all()}
    account_ids = set()
    for e in entries:
        for line in e.lines:
            account_ids.add(line.account_id)
    accounts = (
        {a.id: a for a in db.scalars(select(Account).where(Account.id.in_(account_ids))).all()}
        if account_ids
        else {}
    )

    out: List[GeneralJournalEntry] = []
    for entry in entries:
        lines: List[GeneralJournalLine] = []
        for line in entry.lines:
            # فلتر المشروع يسري على مستوى السطر (مركز التكلفة)
            if cc_id is not None and line.cost_center_id != cc_id:
                continue
            acc = accounts.get(line.account_id)
            lines.append(
                GeneralJournalLine(
                    account_code=acc.code if acc else "—",
                    account_name=acc.name if acc else "—",
                    name=line.name,
                    debit=line.debit,
                    credit=line.credit,
                )
            )
        if not lines:
            continue
        total_d = sum(l.debit for l in lines)
        total_c = sum(l.credit for l in lines)
        journal = journals.get(entry.journal_id)
        out.append(
            GeneralJournalEntry(
                entry_id=entry.id,
                entry_number=entry.entry_number,
                entry_date=entry.entry_date,
                journal_code=journal.code if journal else None,
                journal_name=journal.name if journal else None,
                reference=entry.reference,
                narration=entry.narration,
                state=entry.state,
                lines=lines,
                total_debit=total_d,
                total_credit=total_c,
                is_balanced=total_d == total_c,
            )
        )

    grand_d = sum(e.total_debit for e in out)
    grand_c = sum(e.total_credit for e in out)

    return GeneralJournalReport(
        from_date=from_date,
        to_date=to_date,
        fiscal_year_id=fiscal_year_id,
        project_id=project_id,
        journal_id=journal_id,
        entries=out,
        entries_count=len(out),
        grand_debit=grand_d,
        grand_credit=grand_c,
        is_balanced=grand_d == grand_c,
    )

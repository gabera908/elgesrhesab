"""اليومية الأمريكية — قيود اليومية بأعمدة مدين/دائن مع مجاميع."""
import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_permission
from app.database import get_db
from app.models.account import Account
from app.models.journal import JournalEntry, MoveLine
from app.api.report_filters import resolve_project_cost_center

router = APIRouter(prefix="/api/reports/american-journal", tags=["اليومية الأمريكية"])


class AmericanLine(BaseModel):
    entry_number: str
    entry_date: date
    account_code: str
    account_name: str
    narration: Optional[str]
    debit: Decimal
    credit: Decimal


class AmericanDayGroup(BaseModel):
    entry_date: date
    lines: List[AmericanLine]
    day_debit: Decimal
    day_credit: Decimal


class AmericanJournal(BaseModel):
    from_date: date
    to_date: date
    groups: List[AmericanDayGroup]
    grand_debit: Decimal
    grand_credit: Decimal
    is_balanced: bool


@router.get("", response_model=AmericanJournal)
@router.get("/", response_model=AmericanJournal)
async def american_journal(
    from_date: date = Query(...),
    to_date: date = Query(...),
    journal_id: Optional[uuid.UUID] = Query(None),
    project_id: Optional[uuid.UUID] = Query(None),
    current_user: Account = Depends(require_permission("reports", "read")),
    db: Session = Depends(get_db),
):
    """اليومية الأمريكية — تجميع القيود حسب اليوم مع المجاميع (يدعم فلتر المشروع)."""
    if from_date > to_date:
        raise HTTPException(status_code=422, detail="تاريخ البدء بعد تاريخ الانتهاء")

    cc_id = resolve_project_cost_center(db, project_id)
    stmt = (
        select(MoveLine, JournalEntry, Account)
        .join(JournalEntry, JournalEntry.id == MoveLine.entry_id)
        .join(Account, Account.id == MoveLine.account_id)
        .where(JournalEntry.state == "posted")
        .where(JournalEntry.entry_date.between(from_date, to_date))
        .order_by(JournalEntry.entry_date, JournalEntry.entry_number)
    )
    if journal_id is not None:
        stmt = stmt.where(JournalEntry.journal_id == journal_id)
    if cc_id is not None:
        stmt = stmt.where(MoveLine.cost_center_id == cc_id)

    rows = db.execute(stmt).all()

    by_day: dict[date, List[AmericanLine]] = {}
    for line, entry, account in rows:
        by_day.setdefault(entry.entry_date, []).append(
            AmericanLine(
                entry_number=entry.entry_number,
                entry_date=entry.entry_date,
                account_code=account.code,
                account_name=account.name,
                narration=entry.narration,
                debit=line.debit,
                credit=line.credit,
            )
        )

    groups = [
        AmericanDayGroup(
            entry_date=d,
            lines=lines,
            day_debit=sum(l.debit for l in lines),
            day_credit=sum(l.credit for l in lines),
        )
        for d, lines in sorted(by_day.items())
    ]

    grand_d = sum(g.day_debit for g in groups)
    grand_c = sum(g.day_credit for g in groups)

    return AmericanJournal(
        from_date=from_date,
        to_date=to_date,
        groups=groups,
        grand_debit=grand_d,
        grand_credit=grand_c,
        is_balanced=grand_d == grand_c,
    )

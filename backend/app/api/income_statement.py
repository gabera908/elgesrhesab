"""قائمة الدخل — الإيرادات والمصروفات وصافي الربح."""
import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_permission
from app.database import get_db
from app.models.account import Account
from app.models.journal import JournalEntry, MoveLine

router = APIRouter(prefix="/api/reports/income-statement", tags=["قائمة الدخل"])


class IncomeLine(BaseModel):
    account_code: str
    account_name: str
    debit: Decimal
    credit: Decimal
    balance: Decimal


class IncomeSection(BaseModel):
    section: str
    label: str
    lines: List[IncomeLine]
    total: Decimal


class IncomeStatement(BaseModel):
    from_date: date
    to_date: date
    revenues: List[IncomeSection]
    expenses: List[IncomeSection]
    total_revenues: Decimal
    total_expenses: Decimal
    net_profit: Decimal
    is_loss: bool


@router.get("", response_model=IncomeStatement)
@router.get("/", response_model=IncomeStatement)
async def income_statement(
    from_date: date = Query(...),
    to_date: date = Query(...),
    current_user: Account = Depends(require_permission("reports", "read")),
    db: Session = Depends(get_db),
):
    """قائمة الدخل — كل الإيرادات والمصروفات في الفترة."""
    if from_date > to_date:
        raise HTTPException(status_code=422, detail="تاريخ البدء بعد تاريخ الانتهاء")

    balances = db.execute(
        select(
            MoveLine.account_id,
            func.coalesce(func.sum(MoveLine.debit), 0).label("d"),
            func.coalesce(func.sum(MoveLine.credit), 0).label("c"),
        )
        .join(JournalEntry, JournalEntry.id == MoveLine.entry_id)
        .where(JournalEntry.state == "posted")
        .where(JournalEntry.entry_date.between(from_date, to_date))
        .group_by(MoveLine.account_id)
    ).all()

    bal = {r.account_id: (Decimal(r.d), Decimal(r.c)) for r in balances}
    accounts = {
        a.id: a
        for a in db.scalars(
            select(Account).where(
                Account.is_active == True,  # noqa: E712
                Account.account_type.in_(("income", "expense")),
            )
        ).all()
    }

    revenues: dict[str, List[IncomeLine]] = {}
    expenses: dict[str, List[IncomeLine]] = {}

    for acc in accounts.values():
        d, c = bal.get(acc.id, (Decimal(0), Decimal(0)))
        if acc.account_type == "income":
            value = c - d  # الإيراد طبيعته دائنة
        else:
            value = d - c  # المصروف طبيعته مدينة
        if value == 0:
            continue

        line = IncomeLine(
            account_code=acc.code,
            account_name=acc.name,
            debit=d,
            credit=c,
            balance=value,
        )
        key = acc.statement_section or ("is_revenue" if acc.account_type == "income" else "is_expense")
        if acc.account_type == "income":
            revenues.setdefault(key, []).append(line)
        else:
            expenses.setdefault(key, []).append(line)

    SECTION_LABELS = {
        "is_revenue": "الإيرادات",
        "is_expense": "المصروفات",
    }

    rev_sections = [
        IncomeSection(
            section=k,
            label=SECTION_LABELS.get(k, k),
            lines=lines,
            total=sum(l.balance for l in lines),
        )
        for k, lines in revenues.items()
    ]
    exp_sections = [
        IncomeSection(
            section=k,
            label=SECTION_LABELS.get(k, k),
            lines=lines,
            total=sum(l.balance for l in lines),
        )
        for k, lines in expenses.items()
    ]

    total_rev = sum(s.total for s in rev_sections)
    total_exp = sum(s.total for s in exp_sections)

    return IncomeStatement(
        from_date=from_date,
        to_date=to_date,
        revenues=rev_sections,
        expenses=exp_sections,
        total_revenues=total_rev,
        total_expenses=total_exp,
        net_profit=total_rev - total_exp,
        is_loss=(total_rev - total_exp) < 0,
    )

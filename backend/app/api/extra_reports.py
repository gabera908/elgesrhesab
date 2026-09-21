"""تقارير إضافية — ميزان مراكز التكلفة، كشف الشريك، مقارنة الدخل."""
import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_permission
from app.database import get_db
from app.models.account import Account, CostCenter
from app.models.journal import JournalEntry, MoveLine
from app.models.partner import Partner
from app.models.user import User
from app.api.report_filters import resolve_project_cost_center

router = APIRouter(prefix="/api/reports/extra", tags=["تقارير إضافية"])


# ===== ميزان المراجعة حسب مركز التكلفة =====
class CostCenterBalance(BaseModel):
    cost_center_id: uuid.UUID
    cost_center_code: str
    cost_center_name: str
    total_debit: Decimal
    total_credit: Decimal
    net: Decimal


class CostCenterTrialBalance(BaseModel):
    from_date: date
    to_date: date
    items: List[CostCenterBalance]
    grand_debit: Decimal
    grand_credit: Decimal


@router.get("/cost-center-trial-balance", response_model=CostCenterTrialBalance)
async def cost_center_trial_balance(
    from_date: date = Query(...),
    to_date: date = Query(...),
    current_user: User = Depends(require_permission("reports", "read")),
    db: Session = Depends(get_db),
):
    """ميزان المراجعة مجمّع حسب مراكز التكلفة."""
    rows = db.execute(
        select(
            MoveLine.cost_center_id,
            func.coalesce(func.sum(MoveLine.debit), 0).label("d"),
            func.coalesce(func.sum(MoveLine.credit), 0).label("c"),
        )
        .join(JournalEntry, JournalEntry.id == MoveLine.entry_id)
        .where(JournalEntry.state == "posted")
        .where(JournalEntry.entry_date.between(from_date, to_date))
        .where(MoveLine.cost_center_id.isnot(None))
        .group_by(MoveLine.cost_center_id)
    ).all()

    centers = {
        c.id: c for c in db.scalars(select(CostCenter).where(CostCenter.is_active == True)).all()  # noqa: E712
    }

    items = []
    for r in rows:
        cc = centers.get(r.cost_center_id)
        if cc is None:
            continue
        d, c = Decimal(r.d), Decimal(r.c)
        items.append(
            CostCenterBalance(
                cost_center_id=cc.id,
                cost_center_code=cc.code,
                cost_center_name=cc.name,
                total_debit=d,
                total_credit=c,
                net=d - c,
            )
        )

    return CostCenterTrialBalance(
        from_date=from_date,
        to_date=to_date,
        items=items,
        grand_debit=sum(i.total_debit for i in items),
        grand_credit=sum(i.total_credit for i in items),
    )


# ===== كشف حساب الشريك =====
class PartnerLine(BaseModel):
    entry_number: str
    entry_date: date
    account_code: str
    account_name: str
    narration: Optional[str]
    debit: Decimal
    credit: Decimal
    running_balance: Decimal


class PartnerStatement(BaseModel):
    partner: dict
    from_date: date
    to_date: date
    opening_balance: Decimal
    lines: List[PartnerLine]
    total_debit: Decimal
    total_credit: Decimal
    closing_balance: Decimal


@router.get("/partner-statement", response_model=PartnerStatement)
async def partner_statement(
    partner_id: uuid.UUID = Query(...),
    from_date: date = Query(...),
    to_date: date = Query(...),
    current_user: User = Depends(require_permission("reports", "read")),
    db: Session = Depends(get_db),
):
    """كشف حساب شريك (عميل/مورد/جهة مانحة) مع الرصيد الجاري."""
    from fastapi import HTTPException

    partner = db.get(Partner, partner_id)
    if partner is None:
        raise HTTPException(status_code=404, detail="الشريك غير موجود")

    opening = db.execute(
        select(func.coalesce(func.sum(MoveLine.debit - MoveLine.credit), 0))
        .join(JournalEntry, JournalEntry.id == MoveLine.entry_id)
        .where(JournalEntry.state == "posted")
        .where(MoveLine.partner_id == partner_id)
        .where(JournalEntry.entry_date < from_date)
    ).scalar_one()

    rows = db.execute(
        select(MoveLine, JournalEntry, Account)
        .join(JournalEntry, JournalEntry.id == MoveLine.entry_id)
        .join(Account, Account.id == MoveLine.account_id)
        .where(JournalEntry.state == "posted")
        .where(MoveLine.partner_id == partner_id)
        .where(JournalEntry.entry_date.between(from_date, to_date))
        .order_by(JournalEntry.entry_date, JournalEntry.entry_number)
    ).all()

    lines = []
    running = Decimal(opening)
    for line, entry, account in rows:
        running += line.debit - line.credit
        lines.append(
            PartnerLine(
                entry_number=entry.entry_number,
                entry_date=entry.entry_date,
                account_code=account.code,
                account_name=account.name,
                narration=entry.narration,
                debit=line.debit,
                credit=line.credit,
                running_balance=running,
            )
        )

    total_d = sum(l.debit for l in lines)
    total_c = sum(l.credit for l in lines)

    return PartnerStatement(
        partner={"id": str(partner.id), "code": partner.code, "name": partner.name,
                 "partner_type": partner.partner_type},
        from_date=from_date,
        to_date=to_date,
        opening_balance=Decimal(opening),
        lines=lines,
        total_debit=total_d,
        total_credit=total_c,
        closing_balance=Decimal(opening) + total_d - total_c,
    )


# ===== قائمة الدخل مع مقارنة الفترة السابقة =====
class PeriodComparison(BaseModel):
    label: str
    from_date: date
    to_date: date
    total_revenues: Decimal
    total_expenses: Decimal
    net_profit: Decimal


class IncomeComparison(BaseModel):
    current: PeriodComparison
    previous: PeriodComparison
    revenue_change: Decimal
    revenue_change_pct: Optional[float]
    expense_change: Decimal
    expense_change_pct: Optional[float]
    profit_change: Decimal


def _income_totals(db: Session, from_date: date, to_date: date, cc_id=None) -> tuple[Decimal, Decimal]:
    stmt = (
        select(
            Account.account_type,
            func.coalesce(func.sum(MoveLine.debit), 0).label("d"),
            func.coalesce(func.sum(MoveLine.credit), 0).label("c"),
        )
        .join(MoveLine, MoveLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == MoveLine.entry_id)
        .where(JournalEntry.state == "posted")
        .where(JournalEntry.entry_date.between(from_date, to_date))
        .where(Account.account_type.in_(("income", "expense")))
    )
    if cc_id is not None:
        stmt = stmt.where(MoveLine.cost_center_id == cc_id)
    rows = db.execute(stmt.group_by(Account.account_type)).all()

    rev = Decimal(0)
    exp = Decimal(0)
    for r in rows:
        if r.account_type == "income":
            rev += Decimal(r.c) - Decimal(r.d)
        else:
            exp += Decimal(r.d) - Decimal(r.c)
    return rev, exp


@router.get("/income-comparison", response_model=IncomeComparison)
async def income_comparison(
    from_date: date = Query(...),
    to_date: date = Query(...),
    project_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(require_permission("reports", "read")),
    db: Session = Depends(get_db),
):
    """قائمة الدخل مع مقارنة بالفترة السابقة (نفس المدة) — يدعم فلتر المشروع."""
    from datetime import timedelta

    cc_id = resolve_project_cost_center(db, project_id)
    duration = (to_date - from_date).days + 1
    prev_to = from_date - timedelta(days=1)
    prev_from = prev_to - timedelta(days=duration - 1)

    cur_rev, cur_exp = _income_totals(db, from_date, to_date, cc_id)
    prev_rev, prev_exp = _income_totals(db, prev_from, prev_to, cc_id)

    cur_profit = cur_rev - cur_exp
    prev_profit = prev_rev - prev_exp

    def pct(new: Decimal, old: Decimal) -> Optional[float]:
        if old == 0:
            return None
        return float((new - old) / abs(old) * 100)

    return IncomeComparison(
        current=PeriodComparison(
            label="الفترة الحالية", from_date=from_date, to_date=to_date,
            total_revenues=cur_rev, total_expenses=cur_exp, net_profit=cur_profit,
        ),
        previous=PeriodComparison(
            label="الفترة السابقة", from_date=prev_from, to_date=prev_to,
            total_revenues=prev_rev, total_expenses=prev_exp, net_profit=prev_profit,
        ),
        revenue_change=cur_rev - prev_rev,
        revenue_change_pct=pct(cur_rev, prev_rev),
        expense_change=cur_exp - prev_exp,
        expense_change_pct=pct(cur_exp, prev_exp),
        profit_change=cur_profit - prev_profit,
    )

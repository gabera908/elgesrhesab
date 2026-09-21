"""واجهات المخرجات والتقارير — ميزان المراجعة والأستاذ العام والميزانية."""
import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_permission
from app.database import get_db
from app.models.account import Account
from app.models.journal import JournalEntry, MoveLine
from app.api.report_filters import resolve_project_cost_center

router = APIRouter(prefix="/api/reports", tags=["التقارير"])


class AccountBalance(BaseModel):
    account_id: uuid.UUID
    code: str
    name: str
    level: int
    account_type: str
    opening_debit: Decimal
    opening_credit: Decimal
    period_debit: Decimal
    period_credit: Decimal
    closing_debit: Decimal
    closing_credit: Decimal


class TrialBalance(BaseModel):
    from_date: date
    to_date: date
    accounts: List[AccountBalance]
    total_opening_debit: Decimal
    total_opening_credit: Decimal
    total_period_debit: Decimal
    total_period_credit: Decimal
    total_closing_debit: Decimal
    total_closing_credit: Decimal
    is_balanced: bool


def _period_balances(db: Session, from_date: date, to_date: date, cc_id=None):
    """يجلب الحركات المُرحَّلة المجمَّعة لكل حساب (مع فلتر مركز تكلفة اختياري)."""
    stmt = (
        select(
            MoveLine.account_id,
            func.coalesce(func.sum(MoveLine.debit), 0).label("period_debit"),
            func.coalesce(func.sum(MoveLine.credit), 0).label("period_credit"),
        )
        .join(JournalEntry, JournalEntry.id == MoveLine.entry_id)
        .where(JournalEntry.state == "posted")
        .where(JournalEntry.entry_date.between(from_date, to_date))
    )
    if cc_id is not None:
        stmt = stmt.where(MoveLine.cost_center_id == cc_id)
    rows = db.execute(stmt.group_by(MoveLine.account_id)).all()
    return {r.account_id: (Decimal(r.period_debit), Decimal(r.period_credit)) for r in rows}


def _opening_balances(db: Session, before_date: date, cc_id=None):
    """الأرصدة الافتتاحية قبل تاريخ البدء (مع فلتر مركز تكلفة اختياري)."""
    stmt = (
        select(
            MoveLine.account_id,
            func.coalesce(func.sum(MoveLine.debit), 0).label("op_debit"),
            func.coalesce(func.sum(MoveLine.credit), 0).label("op_credit"),
        )
        .join(JournalEntry, JournalEntry.id == MoveLine.entry_id)
        .where(JournalEntry.state == "posted")
        .where(JournalEntry.entry_date < before_date)
    )
    if cc_id is not None:
        stmt = stmt.where(MoveLine.cost_center_id == cc_id)
    rows = db.execute(stmt.group_by(MoveLine.account_id)).all()
    return {r.account_id: (Decimal(r.op_debit), Decimal(r.op_credit)) for r in rows}


@router.get("/trial-balance", response_model=TrialBalance)
async def trial_balance(
    from_date: date = Query(...),
    to_date: date = Query(...),
    project_id: Optional[uuid.UUID] = Query(None),
    current_user: Account = Depends(require_permission("reports", "read")),
    db: Session = Depends(get_db),
):
    """ميزان المراجعة — افتتاحي + حركة + ختامي مع اختبار التوازن (يدعم فلتر المشروع)."""
    if from_date > to_date:
        raise HTTPException(status_code=422, detail="تاريخ البدء بعد تاريخ الانتهاء")

    cc_id = resolve_project_cost_center(db, project_id)
    accounts = db.scalars(select(Account).where(Account.is_active == True)).all()  # noqa: E712
    opening = _opening_balances(db, from_date, cc_id)
    period = _period_balances(db, from_date, to_date, cc_id)

    items: List[AccountBalance] = []
    for acc in accounts:
        op_d, op_c = opening.get(acc.id, (Decimal(0), Decimal(0)))
        pr_d, pr_c = period.get(acc.id, (Decimal(0), Decimal(0)))
        cl_d, cl_c = op_d + pr_d, op_c + pr_c
        if not (op_d or op_c or pr_d or pr_c):
            continue
        items.append(
            AccountBalance(
                account_id=acc.id,
                code=acc.code,
                name=acc.name,
                level=acc.level,
                account_type=acc.account_type,
                opening_debit=op_d,
                opening_credit=op_c,
                period_debit=pr_d,
                period_credit=pr_c,
                closing_debit=cl_d,
                closing_credit=cl_c,
            )
        )

    t_op_d = sum(i.opening_debit for i in items)
    t_op_c = sum(i.opening_credit for i in items)
    t_pr_d = sum(i.period_debit for i in items)
    t_pr_c = sum(i.period_credit for i in items)
    t_cl_d = sum(i.closing_debit for i in items)
    t_cl_c = sum(i.closing_credit for i in items)

    return TrialBalance(
        from_date=from_date,
        to_date=to_date,
        accounts=items,
        total_opening_debit=t_op_d,
        total_opening_credit=t_op_c,
        total_period_debit=t_pr_d,
        total_period_credit=t_pr_c,
        total_closing_debit=t_cl_d,
        total_closing_credit=t_cl_c,
        # اختبار التوازن: المدين = الدائن في كل مرحلة
        is_balanced=(t_op_d == t_op_c and t_pr_d == t_pr_c and t_cl_d == t_cl_c),
    )


class LedgerLine(BaseModel):
    entry_number: str
    entry_date: date
    account_id: uuid.UUID
    debit: Decimal
    credit: Decimal
    name: Optional[str]
    reference: Optional[str]
    running_balance: Decimal


class GeneralLedger(BaseModel):
    account: dict
    from_date: date
    to_date: date
    opening_balance: Decimal
    lines: List[LedgerLine]
    total_debit: Decimal
    total_credit: Decimal
    closing_balance: Decimal


@router.get("/general-ledger", response_model=GeneralLedger)
async def general_ledger(
    account_id: uuid.UUID = Query(...),
    from_date: date = Query(...),
    to_date: date = Query(...),
    project_id: Optional[uuid.UUID] = Query(None),
    current_user: Account = Depends(require_permission("reports", "read")),
    db: Session = Depends(get_db),
):
    """الأستاذ العام — كشف حركة حساب مع الرصيد الجاري (يدعم فلتر المشروع)."""
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="الحساب غير موجود")

    cc_id = resolve_project_cost_center(db, project_id)

    # الرصيد الافتتاحي (بفرض الطبيعة المدينة)
    op_stmt = (
        select(func.coalesce(func.sum(MoveLine.debit - MoveLine.credit), 0))
        .join(JournalEntry, JournalEntry.id == MoveLine.entry_id)
        .where(JournalEntry.state == "posted")
        .where(MoveLine.account_id == account_id)
        .where(JournalEntry.entry_date < from_date)
    )
    if cc_id is not None:
        op_stmt = op_stmt.where(MoveLine.cost_center_id == cc_id)
    op = db.execute(op_stmt).scalar_one()
    opening = Decimal(op)

    stmt = (
        select(MoveLine, JournalEntry)
        .join(JournalEntry, JournalEntry.id == MoveLine.entry_id)
        .where(JournalEntry.state == "posted")
        .where(MoveLine.account_id == account_id)
        .where(JournalEntry.entry_date.between(from_date, to_date))
        .order_by(JournalEntry.entry_date, JournalEntry.entry_number)
    )
    if cc_id is not None:
        stmt = stmt.where(MoveLine.cost_center_id == cc_id)
    rows = db.execute(stmt).all()

    lines: List[LedgerLine] = []
    running = opening
    for line, entry in rows:
        running += line.debit - line.credit
        lines.append(
            LedgerLine(
                entry_number=entry.entry_number,
                entry_date=entry.entry_date,
                account_id=line.account_id,
                debit=line.debit,
                credit=line.credit,
                name=line.name,
                reference=entry.reference,
                running_balance=running,
            )
        )

    total_d = sum(l.debit for l in lines)
    total_c = sum(l.credit for l in lines)

    return GeneralLedger(
        account={
            "id": str(account.id),
            "code": account.code,
            "name": account.name,
            "account_type": account.account_type,
        },
        from_date=from_date,
        to_date=to_date,
        opening_balance=opening,
        lines=lines,
        total_debit=total_d,
        total_credit=total_c,
        closing_balance=opening + total_d - total_c,
    )


class BalanceSheetItem(BaseModel):
    section: str
    accounts: List[dict]
    total: Decimal


class BalanceSheet(BaseModel):
    as_of_date: date
    assets: List[BalanceSheetItem]
    liabilities: List[BalanceSheetItem]
    equity: List[BalanceSheetItem]
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    is_balanced: bool


@router.get("/balance-sheet", response_model=BalanceSheet)
async def balance_sheet(
    as_of_date: date = Query(...),
    project_id: Optional[uuid.UUID] = Query(None),
    current_user: Account = Depends(require_permission("reports", "read")),
    db: Session = Depends(get_db),
):
    """الميزانية العمومية — أصول = خصوم + حقوق ملكية (يدعم فلتر المشروع)."""
    cc_id = resolve_project_cost_center(db, project_id)
    stmt = (
        select(
            MoveLine.account_id,
            func.coalesce(func.sum(MoveLine.debit), 0).label("d"),
            func.coalesce(func.sum(MoveLine.credit), 0).label("c"),
        )
        .join(JournalEntry, JournalEntry.id == MoveLine.entry_id)
        .where(JournalEntry.state == "posted")
        .where(JournalEntry.entry_date <= as_of_date)
    )
    if cc_id is not None:
        stmt = stmt.where(MoveLine.cost_center_id == cc_id)
    balances = db.execute(stmt.group_by(MoveLine.account_id)).all()

    bal = {r.account_id: (Decimal(r.d), Decimal(r.c)) for r in balances}
    accounts = {
        a.id: a for a in db.scalars(select(Account).where(Account.is_active == True)).all()  # noqa: E712
    }

    def build_sections(prefixes: tuple[str, ...]) -> List[BalanceSheetItem]:
        sections: dict[str, list[dict]] = {}
        for acc in accounts.values():
            if acc.statement_section is None or not acc.statement_section.startswith(prefixes):
                continue
            d, c = bal.get(acc.id, (Decimal(0), Decimal(0)))
            # الأصول/المصروفات: الرصيد المدين
            if acc.account_type in ("asset", "expense"):
                value = d - c
            else:
                value = c - d
            if value == 0:
                continue
            sections.setdefault(acc.statement_section, []).append(
                {
                    "code": acc.code,
                    "name": acc.name,
                    "debit": d,
                    "credit": c,
                    "balance": value,
                }
            )
        return [
            BalanceSheetItem(
                section=s,
                accounts=rows,
                total=sum(r["balance"] for r in rows),
            )
            for s, rows in sections.items()
        ]

    assets = build_sections(("bs_current_asset", "bs_noncurrent_asset"))
    liabilities = build_sections(("bs_current_liab", "bs_noncurrent_liab"))
    equity = build_sections(("bs_equity",))

    total_assets = sum(s.total for s in assets)
    total_liabilities = sum(s.total for s in liabilities)
    total_equity = sum(s.total for s in equity)

    return BalanceSheet(
        as_of_date=as_of_date,
        assets=assets,
        liabilities=liabilities,
        equity=equity,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=total_equity,
        # المعادلة المحاسبية الأساسية
        is_balanced=total_assets == (total_liabilities + total_equity),
    )

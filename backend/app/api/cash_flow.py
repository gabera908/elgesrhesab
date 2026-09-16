"""التدفقات النقدية — الطريقة المباشرة عبر الدفاتر النقدية والبنكية."""
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

router = APIRouter(prefix="/api/reports/cash-flow", tags=["التدفقات النقدية"])

# أقسام التدفق
FLOW_CATEGORIES = {
    "operating": "الأنشطة التشغيلية",
    "investing": "الأنشطة الاستثمارية",
    "financing": "الأنشطة التمويلية",
}


class FlowLine(BaseModel):
    account_code: str
    account_name: str
    inflow: Decimal
    outflow: Decimal
    net: Decimal


class FlowSection(BaseModel):
    category: str
    label: str
    lines: List[FlowLine]
    total: Decimal


class CashFlowStatement(BaseModel):
    from_date: date
    to_date: date
    sections: List[FlowSection]
    net_change: Decimal
    opening_cash: Decimal
    closing_cash: Decimal


def _cash_accounts(db: Session) -> dict[uuid.UUID, Account]:
    """الحسابات النقدية والبنكية — استناداً لأقسام الأصول المتداولة."""
    rows = db.scalars(
        select(Account).where(
            Account.is_active == True,  # noqa: E712
            Account.statement_section == "bs_current_asset",
        )
    ).all()
    return {a.id: a for a in rows}


@router.get("", response_model=CashFlowStatement)
@router.get("/", response_model=CashFlowStatement)
async def cash_flow(
    from_date: date = Query(...),
    to_date: date = Query(...),
    current_user: Account = Depends(require_permission("reports", "read")),
    db: Session = Depends(get_db),
):
    """التدفقات النقدية — الحركة النقدية الواردة والصادرة."""
    if from_date > to_date:
        raise HTTPException(status_code=422, detail="تاريخ البدء بعد تاريخ الانتهاء")

    cash = _cash_accounts(db)
    if not cash:
        return CashFlowStatement(
            from_date=from_date,
            to_date=to_date,
            sections=[],
            net_change=Decimal(0),
            opening_cash=Decimal(0),
            closing_cash=Decimal(0),
        )

    # الحركة خلال الفترة
    period = db.execute(
        select(
            MoveLine.account_id,
            func.coalesce(func.sum(MoveLine.debit), 0).label("d"),
            func.coalesce(func.sum(MoveLine.credit), 0).label("c"),
        )
        .join(JournalEntry, JournalEntry.id == MoveLine.entry_id)
        .where(JournalEntry.state == "posted")
        .where(JournalEntry.entry_date.between(from_date, to_date))
        .where(MoveLine.account_id.in_(list(cash.keys())))
        .group_by(MoveLine.account_id)
    ).all()

    # الرصيد الافتتاحي النقدي
    opening = db.execute(
        select(
            func.coalesce(func.sum(MoveLine.debit - MoveLine.credit), 0)
        )
        .join(JournalEntry, JournalEntry.id == MoveLine.entry_id)
        .where(JournalEntry.state == "posted")
        .where(JournalEntry.entry_date < from_date)
        .where(MoveLine.account_id.in_(list(cash.keys())))
    ).scalar_one()

    lines: dict[str, List[FlowLine]] = {}
    for r in period:
        acc = cash.get(r.account_id)
        if acc is None:
            continue
        inflow = Decimal(r.c)
        outflow = Decimal(r.d)
        net = inflow - outflow
        if net == 0:
            continue
        # تصنيف افتراضي: تشغيلي لكل الحسابات النقدية المباشرة
        lines.setdefault("operating", []).append(
            FlowLine(
                account_code=acc.code,
                account_name=acc.name,
                inflow=inflow,
                outflow=outflow,
                net=net,
            )
        )

    sections = [
        FlowSection(
            category=k,
            label=FLOW_CATEGORIES.get(k, k),
            lines=items,
            total=sum(l.net for l in items),
        )
        for k, items in lines.items()
    ]

    net_change = sum(s.total for s in sections)
    opening_cash = Decimal(opening)
    closing_cash = opening_cash + net_change

    return CashFlowStatement(
        from_date=from_date,
        to_date=to_date,
        sections=sections,
        net_change=net_change,
        opening_cash=opening_cash,
        closing_cash=closing_cash,
    )

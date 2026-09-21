"""واجهات شجرة الحسابات — CRUD مع الحفاظ على الهرمية."""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_permission
from app.database import get_db
from app.models.account import ACCOUNT_TYPES, Account, CostCenter

router = APIRouter(prefix="/api/accounts", tags=["شجرة الحسابات"])


class AccountBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=30)
    name: str = Field(..., min_length=1, max_length=200)
    parent_id: Optional[uuid.UUID] = None
    account_type: str
    statement_section: Optional[str] = None
    is_postable: bool = True


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    account_type: Optional[str] = None
    statement_section: Optional[str] = None
    is_postable: Optional[bool] = None
    is_active: Optional[bool] = None


class AccountOut(AccountBase):
    id: uuid.UUID
    level: int
    is_active: bool
    normal_balance: Optional[str] = None

    class Config:
        from_attributes = True


# القسم الافتراضي في القوائم حسب نوع الحساب
_DEFAULT_SECTION = {
    "asset": "bs_current_asset",
    "liability": "bs_current_liab",
    "equity": "bs_equity",
    "income": "is_revenue",
    "expense": "is_expense",
}

# الطبيعة العادية للحساب
_NORMAL_BALANCE = {
    "asset": "debit",
    "expense": "debit",
    "liability": "credit",
    "equity": "credit",
    "income": "credit",
}


@router.get("", response_model=List[AccountOut])
async def list_accounts(
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
    active_only: bool = True,
):
    """جلب كل الحسابات — تبنى الشجرة في الواجهة."""
    stmt = select(Account).order_by(Account.code)
    if active_only:
        stmt = stmt.where(Account.is_active == True)  # noqa: E712
    return db.scalars(stmt).all()


@router.get("/tree")
async def get_tree(
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """يعيد الحسابات على هيئة شجرة هرمية جاهزة."""
    stmt = select(Account).where(Account.is_active == True).order_by(Account.code)  # noqa: E712
    accounts = db.scalars(stmt).all()

    by_id = {a.id: {**a.__dict__, "children": []} for a in accounts}
    tree: List[dict] = []
    for a in accounts:
        node = by_id[a.id]
        # تنظيف قيم SQLAlchemy غير القابلة للتسلسل
        node.pop("_sa_instance_state", None)
        if a.parent_id and a.parent_id in by_id:
            by_id[a.parent_id]["children"].append(node)
        else:
            tree.append(node)
    return tree


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreate,
    current_user: Account = Depends(require_permission("accounts", "create")),
    db: Session = Depends(get_db),
):
    """إنشاء حساب جديد — تحديد المستوى تلقائياً من الأب."""
    if payload.account_type not in ACCOUNT_TYPES:
        raise HTTPException(status_code=422, detail="نوع الحساب غير صالح")

    if db.scalar(select(Account).where(Account.code == payload.code)):
        raise HTTPException(status_code=409, detail="كود الحساب موجود مسبقاً")

    level = 1
    parent = None
    if payload.parent_id:
        parent = db.get(Account, payload.parent_id)
        if parent is None:
            raise HTTPException(status_code=404, detail="الحساب الأب غير موجود")
        if parent.level >= 4:
            raise HTTPException(status_code=422, detail="لا يمكن تجاوز المستوى الرابع")
        level = parent.level + 1

    account = Account(
        code=payload.code,
        name=payload.name,
        parent_id=payload.parent_id,
        level=level,
        account_type=payload.account_type,
        statement_section=payload.statement_section or _DEFAULT_SECTION[payload.account_type],
        is_postable=payload.is_postable,
        normal_balance=_NORMAL_BALANCE[payload.account_type],
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.put("/{account_id}", response_model=AccountOut)
async def update_account(
    account_id: uuid.UUID,
    payload: AccountUpdate,
    current_user: Account = Depends(require_permission("accounts", "update")),
    db: Session = Depends(get_db),
):
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="الحساب غير موجود")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(account, key, value)
    db.commit()
    db.refresh(account)
    return account


@router.post("/{account_id}/deactivate")
async def deactivate_account(
    account_id: uuid.UUID,
    current_user: Account = Depends(require_permission("accounts", "delete")),
    db: Session = Depends(get_db),
):
    """تعطيل الحساب بدل الحذف — حفاظاً على سلامة السجل التاريخي."""
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="الحساب غير موجود")
    account.is_active = False
    db.commit()
    return {"message": "تم تعطيل الحساب"}

class CostCenterCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=30)
    name: str = Field(..., min_length=1, max_length=200)


class CostCenterOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/cost-centers", response_model=List[CostCenterOut])
async def list_cost_centers(
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
    active_only: bool = True,
):
    """قائمة مراكز التكلفة — تُستخدم في المشاريع والقيود (قراءة فقط)."""
    stmt = select(CostCenter).order_by(CostCenter.code)
    if active_only:
        stmt = stmt.where(CostCenter.is_active == True)  # noqa: E712
    return db.scalars(stmt).all()


@router.post("/cost-centers", response_model=CostCenterOut, status_code=status.HTTP_201_CREATED)
async def create_cost_center(
    payload: CostCenterCreate,
    current_user: Account = Depends(require_permission("accounts", "create")),
    db: Session = Depends(get_db),
):
    """إنشاء مركز تكلفة — نواة ربط المشاريع بالحركة المحاسبية."""
    if db.scalar(select(CostCenter).where(CostCenter.code == payload.code)):
        raise HTTPException(status_code=409, detail="كود مركز التكلفة موجود مسبقاً")
    cc = CostCenter(code=payload.code, name=payload.name)
    db.add(cc)
    db.commit()
    db.refresh(cc)
    return cc


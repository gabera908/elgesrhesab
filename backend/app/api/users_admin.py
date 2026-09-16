"""إدارة المستخدمين والأدوار — واجهة مخصصة للمشرفين."""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_permission
from app.core.security import hash_password, is_password_strong
from app.database import get_db
from app.models.rbac import PERMISSION_MODULES, Role, UserPermission
from app.models.user import User

router = APIRouter(prefix="/api/users-admin", tags=["إدارة المستخدمين"])

# الإجراءات المعتمدة — نفس نطاق صلاحيات الأدوار في seed.py
ALLOWED_ACTIONS = ("read", "create", "update", "delete", "post", "cancel")


class PermissionIn(BaseModel):
    module: str = Field(..., max_length=50)
    action: str = Field(..., max_length=30)


class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=3, max_length=150)
    email: EmailStr
    username: str = Field(..., min_length=4, max_length=100)
    password: str = Field(..., min_length=10)
    role_id: uuid.UUID
    permissions: List[PermissionIn] = []


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=3, max_length=150)
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=4, max_length=100)
    password: Optional[str] = Field(None, min_length=10)
    role_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None
    permissions: Optional[List[PermissionIn]] = None


def _validate_permissions(permissions: List[PermissionIn]) -> None:
    """يتحقق من أن كل صلاحية ضمن الوحدات والإجراءات المعتمدة."""
    for perm in permissions:
        if perm.module not in PERMISSION_MODULES:
            raise HTTPException(
                status_code=422, detail=f"وحدة الصلاحية غير صالحة: {perm.module}"
            )
        if perm.action not in ALLOWED_ACTIONS:
            raise HTTPException(
                status_code=422, detail=f"الإجراء غير صالح: {perm.action}"
            )


def _user_out(user: User) -> dict:
    """تمثيل المستخدم مع اسم دوره وصلاحياته الفردية."""
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "username": user.username,
        "role_id": user.role_id,
        "role_name": user.role.name if user.role else None,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "twofa_enabled": user.twofa_enabled,
        "user_permissions": [
            {"module": p.module, "action": p.action} for p in user.user_permissions
        ],
    }


@router.get("/users")
async def list_users(
    current_user: User = Depends(require_permission("settings", "update")),
    db: Session = Depends(get_db),
):
    """قائمة المستخدمين مع أدوارهم وصلاحياتهم الفردية."""
    users = db.scalars(select(User).order_by(User.full_name)).all()
    return [_user_out(u) for u in users]


@router.get("/roles")
async def list_roles(
    current_user: User = Depends(require_permission("settings", "update")),
    db: Session = Depends(get_db),
):
    """قائمة الأدوار مع صلاحيات كل دور."""
    roles = db.scalars(select(Role).order_by(Role.name)).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "is_system": r.is_system,
            "permissions": [
                {"module": p.module, "action": p.action} for p in r.permissions
            ],
        }
        for r in roles
    ]


@router.get("/permission-modules")
async def get_permission_modules(
    current_user: User = Depends(require_permission("settings", "update")),
):
    """الوحدات والإجراءات المتاحة لبناء مربعات الاختيار في الواجهة."""
    return {"modules": list(PERMISSION_MODULES), "actions": list(ALLOWED_ACTIONS)}


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    current_user: User = Depends(require_permission("settings", "update")),
    db: Session = Depends(get_db),
):
    """إنشاء مستخدم جديد مع دور وصلاحيات فردية اختيارية."""
    strong, msg = is_password_strong(payload.password)
    if not strong:
        raise HTTPException(status_code=422, detail=msg)

    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status_code=409, detail="البريد الإلكتروني مسجَّل مسبقاً")
    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(status_code=409, detail="اسم المستخدم مسجَّل مسبقاً")
    if db.get(Role, payload.role_id) is None:
        raise HTTPException(status_code=422, detail="الدور غير موجود")

    _validate_permissions(payload.permissions)

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        username=payload.username,
        password_hash=hash_password(payload.password),
        role_id=payload.role_id,
    )
    db.add(user)
    db.flush()

    for perm in payload.permissions:
        db.add(UserPermission(user_id=user.id, module=perm.module, action=perm.action))

    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.put("/users/{user_id}")
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    current_user: User = Depends(require_permission("settings", "update")),
    db: Session = Depends(get_db),
):
    """تحديث مستخدم — البيانات الأساسية، الدور، الحالة، أو الصلاحيات الفردية."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    data = payload.model_dump(exclude_unset=True)

    if "is_active" in data and data["is_active"] is False and user.id == current_user.id:
        raise HTTPException(status_code=400, detail="لا يمكنك تعطيل حسابك الخاص")

    if data.get("email"):
        other = db.scalar(select(User).where(User.email == data["email"]))
        if other and other.id != user.id:
            raise HTTPException(status_code=409, detail="البريد الإلكتروني مسجَّل مسبقاً")

    if data.get("username"):
        other = db.scalar(select(User).where(User.username == data["username"]))
        if other and other.id != user.id:
            raise HTTPException(status_code=409, detail="اسم المستخدم مسجَّل مسبقاً")

    if data.get("role_id") and db.get(Role, data["role_id"]) is None:
        raise HTTPException(status_code=422, detail="الدور غير موجود")

    if data.get("password"):
        strong, msg = is_password_strong(data["password"])
        if not strong:
            raise HTTPException(status_code=422, detail=msg)
        user.password_hash = hash_password(data["password"])

    if "permissions" in data:
        perms = data["permissions"] or []
        _validate_permissions(perms)
        user.user_permissions.clear()
        db.flush()
        for perm in perms:
            db.add(UserPermission(user_id=user.id, module=perm.module, action=perm.action))

    for key in ("full_name", "email", "username", "role_id", "is_active"):
        if key in data and data[key] is not None:
            setattr(user, key, data[key])

    db.commit()
    db.refresh(user)
    return _user_out(user)
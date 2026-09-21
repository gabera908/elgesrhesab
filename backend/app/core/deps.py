"""التبعيات المشتركة: المستخدم الحالي، الصلاحيات، تسجيل التدقيق."""
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import decode_token
from app.core.security import ACCESS_COOKIE_NAME
from app.database import get_db
from app.models.rbac import AuditLog, Permission, UserPermission
from app.models.user import User


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
) -> User:
    """يستخرج المستخدم من كوكي HttpOnly أولاً ثم Bearer للتوافق مع العملاء القدامى."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="بيانات الاعتماد غير صحيحة",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token: Optional[str] = request.cookies.get(ACCESS_COOKIE_NAME)
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise credentials_exception

    payload = decode_token(token)

    if payload is None or payload.get("type") != "access":
        raise credentials_exception

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    user = db.get(User, uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise credentials_exception

    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(status_code=403, detail="الحساب مقفل مؤقتاً بسبب محاولات فاشلة")

    return user


def require_permission(module: str, action: str) -> Callable:
    """يتحقق من صلاحية module:action لدور المستخدم أو أذوناته الفردية."""

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_superuser:
            return current_user

        role_perms = {f"{p.module}:{p.action}" for p in (current_user.role.permissions or [])}
        user_perms = {
            f"{p.module}:{p.action}" for p in (current_user.user_permissions or [])
        }
        if f"{module}:{action}" in role_perms or f"{module}:{action}" in user_perms:
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"ليس لديك صلاحية {module}:{action}",
        )

    return checker


def audit_action(module: str, action: str) -> Callable:
    """يزيّن المسار ليسجّل العملية في سجل التدقيق غير القابل للحذف."""

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            request: Request = kwargs.get("request")
            current_user: Optional[User] = kwargs.get("current_user")
            db: Optional[Session] = kwargs.get("db")
            result = await func(*args, **kwargs)

            if db is not None:
                log = AuditLog(
                    user_id=current_user.id if current_user else None,
                    action=action,
                    module=module,
                    ip_address=request.client.host if request and request.client else None,
                    user_agent=request.headers.get("user-agent") if request else None,
                )
                db.add(log)
                db.commit()
            return result

        return wrapper

    return decorator

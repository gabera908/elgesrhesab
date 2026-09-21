"""تسجيل الدخول والتسجيل — مصادقة آمنة."""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user
from app.core.security import (
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_2fa_secret,
    hash_password,
    is_password_strong,
    set_auth_cookies,
    verify_2fa_code,
    verify_password,
)
from app.database import get_db
from app.models.rbac import Role
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["المصادقة"])

limiter = Limiter(key_func=get_remote_address)

# قفل الحساب بعد 5 محاولات فاشلة
MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION_MINUTES = 15
LOGIN_RATE = f"{settings.login_rate_limit_per_minute}/minute"


def _register_failed_attempt(user: User, db: Session) -> None:
    """يسجّل محاولة فاشلة ويقفل الحساب عند تجاوز الحد."""
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
        user.locked_until = datetime.now(timezone.utc) + timedelta(
            minutes=LOCK_DURATION_MINUTES
        )
    db.commit()


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=3, max_length=150)
    email: EmailStr
    username: str = Field(..., min_length=4, max_length=100)
    password: str = Field(..., min_length=10)


class LoginRequest(BaseModel):
    username: str
    password: str
    twofa_code: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    twofa_required: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class Enable2FARequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """تسجيل مستخدم جديد — يتطلب كلمة مرور قوية، ولا يسمح بالتكرار."""
    strong, msg = is_password_strong(payload.password)
    if not strong:
        raise HTTPException(status_code=422, detail=msg)

    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status_code=409, detail="البريد الإلكتروني مسجَّل مسبقاً")
    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(status_code=409, detail="اسم المستخدم مسجَّل مسبقاً")

    # أول مستخدم = مدير أعلى، يأخذ دور admin
    is_first = db.scalar(select(User).limit(1)) is None
    role = None
    if is_first:
        role = db.scalar(select(Role).where(Role.name == "admin"))
        if role is None:
            role = Role(name="admin", description="مدير النظام", is_system=True)
            db.add(role)
            db.flush()

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        username=payload.username,
        password_hash=hash_password(payload.password),
        role_id=role.id if role else None,
        is_superuser=is_first,
    )
    db.add(user)
    db.commit()
    return {"message": "تم التسجيل بنجاح", "is_admin": is_first}


@limiter.limit(LOGIN_RATE)
@router.post("/login")
async def login(
    request: Request, response: Response, payload: LoginRequest, db: Session = Depends(get_db)
):
    """تسجيل الدخول مع حماية من القوة الغاشمة و2FA."""
    user = db.scalar(select(User).where(User.username == payload.username))

    # رسالة موحَّدة لمنع كشف وجود الحساب
    invalid = HTTPException(status_code=401, detail="بيانات الاعتماد غير صحيحة")

    # كلمة مرور خاطئة أو مستخدم غير موجود ⇒ سجّل محاولة عند وجود المستخدم
    if user is None or not verify_password(payload.password, user.password_hash):
        if user is not None:
            _register_failed_attempt(user, db)
            if user.locked_until and user.locked_until > datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=403,
                    detail="الحساب مقفل مؤقتاً بسبب محاولات فاشلة",
                )
        raise invalid

    if not user.is_active:
        raise HTTPException(status_code=403, detail="الحساب غير نشط")

    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(status_code=403, detail="الحساب مقفل مؤقتاً")

    # التحقق من 2FA عند التفعيل
    if user.twofa_enabled:
        if not payload.twofa_code:
            return TokenResponse(
                access_token="",
                refresh_token="",
                twofa_required=True,
            )
        if not user.twofa_secret or not verify_2fa_code(user.twofa_secret, payload.twofa_code):
            _register_failed_attempt(user, db)
            raise HTTPException(status_code=401, detail="رمز التحقق غير صحيح")

    # إعادة تصفير المحاولات
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    role = user.role.name if user.role else "viewer"
    access_token = create_access_token(user.id, role)
    refresh_token = create_refresh_token(user.id)
    set_auth_cookies(response, access_token, refresh_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    payload: RefreshRequest | None = None,
    db: Session = Depends(get_db),
):
    """تجديد رمز الوصول عبر رمز التحديث (كوكي HttpOnly أولاً ثم body للتوافق)."""
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_token and payload is not None:
        raw_token = payload.refresh_token
    if not raw_token:
        raise HTTPException(status_code=401, detail="رمز التحديث غير صالح")
    data = decode_token(raw_token)
    if data is None or data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="رمز التحديث غير صالح")

    user = db.get(User, data["sub"])
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="المستخدم غير موجود")

    role = user.role.name if user.role else "viewer"
    access_token = create_access_token(user.id, role)
    refresh_token = create_refresh_token(user.id)
    set_auth_cookies(response, access_token, refresh_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/logout")
async def logout(response: Response, current_user: User = Depends(get_current_user)):
    """تسجيل الخروج — يمسح كوكيز HttpOnly."""
    clear_auth_cookies(response)
    return {"message": "تم تسجيل الخروج"}


@router.post("/2fa/enable")
async def enable_2fa(
    payload: Enable2FARequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """تفعيل المصادقة الثنائية — توليد السر والتحقق منه."""
    if not current_user.twofa_secret:
        current_user.twofa_secret = generate_2fa_secret()
        db.commit()

    if not verify_2fa_code(current_user.twofa_secret, payload.code):
        raise HTTPException(status_code=400, detail="رمز التحقق غير صحيح")

    current_user.twofa_enabled = True
    db.commit()
    return {"message": "تم تفعيل المصادقة الثنائية"}


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "role": current_user.role.name if current_user.role else None,
        "twofa_enabled": current_user.twofa_enabled,
        "is_superuser": current_user.is_superuser,
    }

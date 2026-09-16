"""طبقة الأمان — كلمات المرور (Argon2id) و JWT و 2FA."""
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import pyotp
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# Argon2id — أقوى من bcrypt لمقاومة هجمات GPU
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# ===== كلمات المرور =====
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ===== JWT =====
def _create_token(
    subject: str | uuid.UUID,
    token_type: str,
    expires_delta: timedelta,
    extra: Optional[dict[str, Any]] = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": secrets.token_urlsafe(16),  # معرّف فلسي لكل رمز (للإبطال)
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    return _create_token(
        user_id,
        "access",
        timedelta(minutes=settings.jwt_access_expire_minutes),
        {"role": role},
    )


def create_refresh_token(user_id: uuid.UUID) -> str:
    return _create_token(
        user_id,
        "refresh",
        timedelta(days=settings.jwt_refresh_expire_days),
    )


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """يفك تشفير الرمز ويتحقق من صلاحيته ونوعه."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None


# ===== المصادقة الثنائية (TOTP) =====
def generate_2fa_secret() -> str:
    return pyotp.random_base32()


def build_totp_uri(secret: str, email: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=email, issuer_name=settings.twofa_issuer
    )


def verify_2fa_code(secret: str, code: str) -> bool:
    totp = pyotp.totp.TOTP(secret)
    return totp.verify(code, valid_window=1)  # نافذة 30 ثانية للتسامح مع انحراف الساعة


# ===== الأمان العام =====
def generate_secure_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def is_password_strong(password: str) -> tuple[bool, str]:
    """التحقق من قوة كلمة المرور قبل قبولها."""
    if len(password) < 10:
        return False, "كلمة المرور يجب ألا تقل عن 10 أحرف"
    if not any(c.isupper() for c in password):
        return False, "يجب أن تحتوي على حرف كبير واحد على الأقل"
    if not any(c.islower() for c in password):
        return False, "يجب أن تحتوي على حرف صغير واحد على الأقل"
    if not any(c.isdigit() for c in password):
        return False, "يجب أن تحتوي على رقم واحد على الأقل"
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "يجب أن تحتوي على رمز خاص واحد على الأقل"
    return True, ""

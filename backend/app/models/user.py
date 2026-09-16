"""المستخدمون — مصادقة آمنة (Argon2id + 2FA)."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.journal import JournalEntry
    from app.models.rbac import Role, UserPermission


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Argon2id hash — لا تخزَّن كلمات المرور صريحة أبداً
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # المصادقة الثنائية
    twofa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    twofa_secret: Mapped[Optional[str]] = mapped_column(String(64))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # حماية ضد هجمات القوة الغاشمة
    failed_login_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column()

    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)

    role: Mapped["Role"] = relationship(back_populates="users")
    user_permissions: Mapped[List["UserPermission"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    entries: Mapped[List["JournalEntry"]] = relationship(
        back_populates="created_by_user", foreign_keys="JournalEntry.created_by"
    )

    def __repr__(self) -> str:
        return f"<User {self.username}>"

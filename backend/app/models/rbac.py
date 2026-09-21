"""المستخدمون والأدوار والصلاحيات وسجل التدقيق."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User

PERMISSION_MODULES = ("accounts", "journals", "partners", "projects", "reports", "settings", "users")


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    # admin / accountant / reviewer / viewer
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    users: Mapped[List["User"]] = relationship(back_populates="role")
    permissions: Mapped[List["Permission"]] = relationship(back_populates="role")

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


class Permission(Base, TimestampMixin):
    """صلاحية دقيقة (module:action) مرتبطة بدور واحد."""

    __tablename__ = "permissions"
    __table_args__ = (UniqueConstraint("role_id", "module", "action"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))
    module: Mapped[str] = mapped_column(String(50), nullable=False)  # accounts, journals...
    action: Mapped[str] = mapped_column(String(30), nullable=False)  # read, create, post...

    role: Mapped["Role"] = relationship(back_populates="permissions")

    def __repr__(self) -> str:
        return f"<Permission {self.module}:{self.action}>"


class UserPermission(Base, TimestampMixin):
    """صلاحية دقيقة (module:action) مرتبطة بمستخدم واحد — تُضاف فوق صلاحيات دوره."""

    __tablename__ = "user_permissions"
    __table_args__ = (UniqueConstraint("user_id", "module", "action"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    module: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)

    user: Mapped["User"] = relationship(back_populates="user_permissions")

    def __repr__(self) -> str:
        return f"<UserPermission {self.module}:{self.action}>"


class AuditLog(Base):
    """سجل تدقيق غير قابل للحذف — يسجّل كل عملية مالية حساسة."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    module: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(String(64))
    entity_type: Mapped[Optional[str]] = mapped_column(String(64))
    details: Mapped[Optional[str]] = mapped_column(Text)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[Optional["User"]] = relationship()

    def __repr__(self) -> str:
        return f"<AuditLog {self.module}:{self.action}>"

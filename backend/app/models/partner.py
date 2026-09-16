"""الشركاء — عملاء/موردون/جهات مانحة مع بيانات ضريبية."""
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.journal import MoveLine

# أنواع الشركاء
PARTNER_TYPES = (
    "customer",  # عميل
    "supplier",  # مورد
    "donor",     # جهة مانحة
    "employee",  # موظف
    "other",     # أخرى
)


class Partner(Base, TimestampMixin):
    """شريك تجاري — عميل/مورد/جهة مانحة."""

    __tablename__ = "partners"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # نوع الشريك
    partner_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # بيانات التواصل (تُعامل كبيانات شخصية)
    phone: Mapped[Optional[str]] = mapped_column(String(30))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    address: Mapped[Optional[str]] = mapped_column(Text)

    # البيانات الضريبية المصرية
    tax_id: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    commercial_register: Mapped[Optional[str]] = mapped_column(String(50))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<Partner {self.code} {self.name}>"

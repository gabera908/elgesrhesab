"""إعدادات المؤسسة — صف واحد فقط لكل قاعدة بيانات."""
from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class Setting(Base, TimestampMixin):
    """صف الإعدادات الوحيد (id ثابت)."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text)
    tax_id: Mapped[Optional[str]] = mapped_column(String(50))
    phone: Mapped[Optional[str]] = mapped_column(String(30))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    currency: Mapped[str] = mapped_column(String(10), default="EGP", nullable=False)
    fiscal_year_start_month: Mapped[int] = mapped_column(default=1, nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500))

    def __repr__(self) -> str:
        return f"<Setting {self.name}>"

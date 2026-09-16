"""الفترات المالية — إقفال الفترات لمنع الترحيل في الماضي."""
import uuid
from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.journal import FiscalYear


class Period(Base, TimestampMixin):
    """فترة مالية (شهر/ربع) داخل سنة مالية — يمكن إقفالها."""

    __tablename__ = "periods"
    __table_args__ = (
        CheckConstraint("start_date <= end_date", name="ck_period_dates"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    fiscal_year_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fiscal_years.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # يناير 2026

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    fiscal_year: Mapped["FiscalYear"] = relationship(back_populates="periods")

    def __repr__(self) -> str:
        return f"<Period {self.name} closed={self.is_closed}>"


class Company(Base, TimestampMixin):
    """بيانات الشركة — صف واحد فعلياً في v1."""

    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200))

    # البيانات الضريبية
    tax_id: Mapped[Optional[str]] = mapped_column(String(50))
    commercial_register: Mapped[Optional[str]] = mapped_column(String(50))

    address: Mapped[Optional[str]] = mapped_column(String(500))
    phone: Mapped[Optional[str]] = mapped_column(String(30))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    website: Mapped[Optional[str]] = mapped_column(String(255))

    currency: Mapped[str] = mapped_column(String(10), default="EGP", nullable=False)
    fiscal_year_start_month: Mapped[int] = mapped_column(default=1, nullable=False)

    logo_url: Mapped[Optional[str]] = mapped_column(String(500))

    def __repr__(self) -> str:
        return f"<Company {self.name}>"

"""القيود اليومية والدفاتر والسنوات المالية — القيد المزدوج الصارم."""
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.account import Account, CostCenter
    from app.models.attachment import Attachment
    from app.models.partner import Partner
    from app.models.period import Period
    from app.models.user import User

# أنواع الدفاتر
JOURNAL_TYPES = (
    "general",    # عام
    "cash",       # نقدي (صناديق)
    "bank",       # بنكي
    "sales",      # مبيعات
    "purchase",   # مشتريات
    "opening",    # افتتاحي
)

# حالات القيد — وفق مخطط سير العمل: مسودة → مراجعة → مرحَّل → معكوس
ENTRY_STATES = ("draft", "in_review", "posted", "reversed")


class Journal(Base, TimestampMixin):
    """الدفتر المحاسبي — يقبل القيود."""

    __tablename__ = "journals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    journal_type: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # الحسابات الافتراضية لتسريع الإدخال
    default_debit_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL")
    )
    default_credit_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL")
    )

    entries: Mapped[List["JournalEntry"]] = relationship(back_populates="journal")

    def __repr__(self) -> str:
        return f"<Journal {self.code} {self.name}>"


class FiscalYear(Base, TimestampMixin):
    """السنة المالية — تقفل الفترات بداخلها."""

    __tablename__ = "fiscal_years"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # 2026
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_closed: Mapped[bool] = mapped_column(default=False, nullable=False)

    periods: Mapped[List["Period"]] = relationship(
        back_populates="fiscal_year", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<FiscalYear {self.name}>"


class JournalEntry(Base, TimestampMixin):
    """القيد اليومي — يجب أن يتوازن (Σdebit = Σcredit) قبل الترحيل."""

    __tablename__ = "journal_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # رقم تسلسلي فريد لكل سنة مالية (Sequence لكل سنة)
    entry_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    sequence_number: Mapped[Optional[int]] = mapped_column()
    journal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("journals.id"), nullable=False)
    fiscal_year_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("fiscal_years.id"))

    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    reference: Mapped[Optional[str]] = mapped_column(String(100))
    narration: Mapped[Optional[str]] = mapped_column(Text)  # البيان/الوصف

    state: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, index=True)

    amount: Mapped[int] = mapped_column(Numeric(18, 2), default=0, nullable=False)

    # تتبع المسؤولية
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    posted_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # القيد الأصلي عند العكس
    reversed_from_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("journal_entries.id", ondelete="SET NULL")
    )

    journal: Mapped["Journal"] = relationship(back_populates="entries")
    lines: Mapped[List["MoveLine"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )
    attachments: Mapped[List["Attachment"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )
    created_by_user: Mapped[Optional["User"]] = relationship(
        foreign_keys=[created_by], back_populates="entries"
    )
    posted_by_user: Mapped[Optional["User"]] = relationship(
        foreign_keys=[posted_by]
    )

    def __repr__(self) -> str:
        return f"<JournalEntry {self.entry_number} {self.state}>"


class MoveLine(Base, TimestampMixin):
    """سطر القيد — إما مدين أو دائن، لا كليهما (قيد صارم)."""

    __tablename__ = "move_lines"
    __table_args__ = (
        # القيد الذهبي للقيد المزدوج
        CheckConstraint("debit >= 0 AND credit >= 0", name="ck_moveline_nonneg"),
        CheckConstraint("(debit > 0 AND credit = 0) OR (debit = 0 AND credit > 0) OR (debit = 0 AND credit = 0)", name="ck_moveline_exclusive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)

    debit: Mapped[int] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    credit: Mapped[int] = mapped_column(Numeric(18, 2), default=0, nullable=False)

    name: Mapped[Optional[str]] = mapped_column(String(200))  # بيان السطر
    partner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("partners.id", ondelete="SET NULL"), index=True
    )
    cost_center_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("cost_centers.id"))
    date_maturity: Mapped[Optional[date]] = mapped_column(Date)

    entry: Mapped["JournalEntry"] = relationship(back_populates="lines")
    account: Mapped["Account"] = relationship(back_populates="move_lines")
    partner: Mapped[Optional["Partner"]] = relationship()
    cost_center: Mapped[Optional["CostCenter"]] = relationship()

    def __repr__(self) -> str:
        return f"<MoveLine {self.account_id} D:{self.debit} C:{self.credit}>"

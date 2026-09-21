"""المشاريع — مشاريع المؤسسة الممولة (Donor → Grant → Project → CostCenter).

مستوحى من أنظمة ERP الاحترافية للمنظمات غير الربحية (ERPNext Non-Profit / Odoo):
- Project: code, name, donor (شريك مانح), grant_reference, program, status,
  start/end_date, budget_total, currency, manager, cost_center, description
- الحالات: draft → active → on_hold → completed → closed (+ cancelled)
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


# حالات المشروع — دورة الحياة الاحترافية
PROJECT_STATUSES = (
    "draft",      # مسودة
    "active",     # نشط
    "on_hold",    # موقوف مؤقتاً
    "completed",  # مكتمل
    "closed",     # مقفل مالياً
    "cancelled",  # ملغي
)


class Project(Base, TimestampMixin):
    """مشروع ممول — يربط المانح والبرنامج ومركز التكلفة والموازنة."""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # الارتباط التمويلي (Donor → Grant)
    donor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("partners.id", ondelete="SET NULL"), index=True
    )
    grant_reference: Mapped[Optional[str]] = mapped_column(String(100))  # رقم المنحة/الاتفاقية
    program: Mapped[Optional[str]] = mapped_column(String(200))  # البرنامج (تعليم/صحة/...)

    # دورة الحياة
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, index=True)

    # المدة
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)

    # الموازنة المعتمدة
    budget_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="EGP", nullable=False)

    # المسؤولية والربط المحاسبي
    manager: Mapped[Optional[str]] = mapped_column(String(200))  # مدير المشروع
    cost_center_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("cost_centers.id", ondelete="SET NULL"), index=True
    )

    description: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Project {self.code} {self.name}>"

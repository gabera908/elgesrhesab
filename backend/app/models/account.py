"""شجرة الحسابات — قلب النظام المحاسبي (4 مستويات)."""
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.journal import MoveLine

# طبيعة الحساب — تحدد موضعه في القوائم المالية
ACCOUNT_TYPES = (
    "asset",       # أصول
    "liability",   # خصوم
    "equity",      # حقوق ملكية
    "income",      # إيرادات
    "expense",     # مصروفات
)

# مكان الحساب في القائمة (للميزانية العمومية / قائمة الدخل)
STATEMENT_SECTIONS = (
    "bs_current_asset",    # أصول متداولة
    "bs_noncurrent_asset", # أصول غير متداولة (ثابتة)
    "bs_current_liab",     # خصوم متداولة
    "bs_noncurrent_liab",  # خصوم غير متداولة
    "bs_equity",           # حقوق الملكية
    "is_revenue",          # إيرادات
    "is_expense",          # مصروفات
)


class Account(Base, TimestampMixin):
    """حساب في الشجرة — يدعم 4 مستويات هرمية."""

    __tablename__ = "accounts"
    __table_args__ = (
        # لا يجتمع مدين ودائن في نفس السطر (قيد القيد المزدوج)
        CheckConstraint("debit_default >= 0 AND credit_default >= 0", name="ck_account_defaults"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # الهرمية: المستوى 1 (رئيسي) حتى 4 (فرعي تفصيلي)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), index=True
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False)

    # التصنيف المحاسبي
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)
    statement_section: Mapped[Optional[str]] = mapped_column(String(30))

    # الحساب قابل للترحيل (يقبل قيوداً) أم مجرد تجميعي
    is_postable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # طبيعة الحساب العادية: مدين (أصول/مصروفات) أو دائن (خصوم/حقوق/إيرادات)
    normal_balance: Mapped[Optional[str]] = mapped_column(String(6))

    # قيم افتراضية للرصيد الافتتاحي
    debit_default: Mapped[int] = mapped_column(default=0, nullable=False)
    credit_default: Mapped[int] = mapped_column(default=0, nullable=False)

    parent: Mapped[Optional["Account"]] = relationship(
        remote_side="Account.id", back_populates="children"
    )
    children: Mapped[List["Account"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
    move_lines: Mapped[List["MoveLine"]] = relationship(back_populates="account")

    def __repr__(self) -> str:
        return f"<Account {self.code} {self.name}>"


class CostCenter(Base, TimestampMixin):
    """مركز تكلفة — يخصَّص عليه المصروفات (مشاريع/برامج المؤسسة)."""

    __tablename__ = "cost_centers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<CostCenter {self.code} {self.name}>"

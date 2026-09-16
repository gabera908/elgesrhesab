"""زرع شجرة الحسابات الافتراضية والدفاتر — نمط محاسبي مصري."""
import uuid

from sqlalchemy import select

from app.database import SessionLocal
from app.models.account import Account
from app.models.journal import Journal
from app.models.rbac import Role
from app.models.user import User
from app.core.security import hash_password
from app.seed import seed_roles

# الشجرة الافتراضية: (code, name, type, section, postable)
DEFAULT_TREE = [
    # المستوى الأول
    ("1", "الأصول", "asset", "bs_current_asset", False),
    ("2", "الخصوم", "liability", "bs_current_liab", False),
    ("3", "حقوق الملكية", "equity", "bs_equity", False),
    ("4", "الإيرادات", "income", "is_revenue", False),
    ("5", "المصروفات", "expense", "is_expense", False),
    # المستوى الثاني — الأصول
    ("1.1", "الأصول المتداولة", "asset", "bs_current_asset", False),
    ("1.2", "الأصول الثابتة", "asset", "bs_noncurrent_asset", False),
    ("1.1.1", "الصندوق", "asset", "bs_current_asset", True),
    ("1.1.2", "البنوك", "asset", "bs_current_asset", False),
    ("1.1.2.1", "البنك الأهلي", "asset", "bs_current_asset", True),
    ("1.1.2.2", "بنك مصر", "asset", "bs_current_asset", True),
    ("1.2.1", "الأثاث والتجهيزات", "asset", "bs_noncurrent_asset", True),
    ("1.2.2", "أجهزة الحاسب", "asset", "bs_noncurrent_asset", True),
    # المستوى الثاني — الخصوم
    ("2.1", "الخصوم المتداولة", "liability", "bs_current_liab", False),
    ("2.1.1", "الموردون", "liability", "bs_current_liab", True),
    ("2.1.2", "مستحقات الموظفين", "liability", "bs_current_liab", True),
    # حقوق الملكية
    ("3.1", "رأس المال", "equity", "bs_equity", True),
    ("3.2", "الأرباح المرحَّلة", "equity", "bs_equity", True),
    # الإيرادات
    ("4.1", "إيرادات النشاط", "income", "is_revenue", False),
    ("4.1.1", "إيرادات المشاريع", "income", "is_revenue", True),
    ("4.1.2", "إيرادات استشارية", "income", "is_revenue", True),
    # المصروفات
    ("5.1", "مصروفات تشغيلية", "expense", "is_expense", False),
    ("5.1.1", "الرواتب والأجور", "expense", "is_expense", True),
    ("5.1.2", "الإيجارات", "expense", "is_expense", True),
    ("5.1.3", "أدوات مكتبية", "expense", "is_expense", True),
    ("5.2", "مصروفات إدارية", "expense", "is_expense", False),
    ("5.2.1", "اتصالات وإنترنت", "expense", "is_expense", True),
    ("5.2.2", "صيانة", "expense", "is_expense", True),
]

# الدفاتر الافتراضية
DEFAULT_JOURNALS = [
    ("GEN", "دفتر اليومية العامة", "general"),
    ("BNK", "دفتر البنوك", "bank"),
    ("CSH", "دفتر الصندوق", "cash"),
    ("SAL", "دفتر المبيعات", "sales"),
    ("PUR", "دفتر المشتريات", "purchase"),
    ("OPN", "دفتر الأرصدة الافتتاحية", "opening"),
]


def _level_from_code(code: str) -> int:
    """المستوى = عدد الأجزاء بعد التقسيم على '.'."""
    return code.count(".") + 1


def _parent_code(code: str) -> str | None:
    parts = code.split(".")
    if len(parts) == 1:
        return None
    return ".".join(parts[:-1])


def seed_chart_of_accounts(db) -> int:
    """ينشئ شجرة الحسابات الافتراضية إن لم تكن موجودة."""
    created = 0
    code_to_id: dict[str, uuid.UUID] = {}

    existing = {
        a.code: a
        for a in db.scalars(select(Account)).all()
    }
    for a in existing.values():
        code_to_id[a.code] = a.id

    for code, name, account_type, section, postable in DEFAULT_TREE:
        if code in existing:
            continue

        parent_code = _parent_code(code)
        parent_id = code_to_id.get(parent_code) if parent_code else None

        account = Account(
            code=code,
            name=name,
            parent_id=parent_id,
            level=_level_from_code(code),
            account_type=account_type,
            statement_section=section,
            is_postable=postable,
            normal_balance="debit" if account_type in ("asset", "expense") else "credit",
        )
        db.add(account)
        db.flush()
        code_to_id[code] = account.id
        created += 1

    db.commit()
    return created


def seed_journals(db) -> int:
    """ينشئ الدفاتر الافتراضية."""
    created = 0
    existing = {j.code for j in db.scalars(select(Journal)).all()}

    # حسابات افتراضية للبنوك والصندوق
    cash_account = db.scalar(select(Account).where(Account.code == "1.1.1"))
    bank_account = db.scalar(select(Account).where(Account.code == "1.1.2.1"))

    for code, name, jtype in DEFAULT_JOURNALS:
        if code in existing:
            continue
        journal = Journal(
            code=code,
            name=name,
            journal_type=jtype,
            default_debit_account_id=cash_account.id if cash_account else None,
            default_credit_account_id=bank_account.id if bank_account else None,
        )
        db.add(journal)
        created += 1

    db.commit()
    return created


def main() -> None:
    db = SessionLocal()
    try:
        seed_roles(db)
        accounts_created = seed_chart_of_accounts(db)
        journals_created = seed_journals(db)
        print("[seed] roles: done")
        print(f"[seed] accounts created: {accounts_created}")
        print(f"[seed] journals created: {journals_created}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

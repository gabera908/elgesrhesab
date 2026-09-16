"""بيانات تجريبية — سيناريو عرض كامل للنظام المحاسبي.

بذر مخطط بيانات تجريبي متكامل يتضمن:
- مركزَي تكلفة (برنامجي المؤسسة).
- سنة مالية 2026 مع الفترات الشهرية الاثنتي عشرة.
- سبعة قيود يومية متوازنة عبر الدفاتر (افتتاحي/نقدي/بنكي/مبيعات/مشتريات)
  بحالات مختلفة (مسودة/قيد المراجعة/مرحَّل).

العملية معرفية (idempotent): إعادة التشغيل لا تُنشئ نسخاً مكررة.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.database import SessionLocal
from app.models.account import Account, CostCenter
from app.models.journal import FiscalYear, Journal, JournalEntry, MoveLine
from app.models.period import Period
from app.models.user import User

# مراكز التكلفة التجريبية
DEMO_COST_CENTERS = [
    ("CC-01", "برنامج بناء القدرات"),
    ("CC-02", "برنامج المساعدات الطارئة"),
]

# أسماء الأشهر المالية
MONTH_NAMES_AR = [
    "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]

# كل قيد: (حساب, مدين, دائن, مركز تكلفة اختياري)
DEMO_ENTRIES = [
    {
        "journal": "OPN",
        "entry_number": "OP-20260101-0001",
        "sequence_number": 1,
        "entry_date": date(2026, 1, 1),
        "reference": "OPENING-BALANCE",
        "narration": "قيد الرصيد الافتتاحي للبنوك والصناديق",
        "state": "posted",
        "lines": [
            ("1.1.1", Decimal("50000.00"), Decimal(0), None),
            ("1.1.2.1", Decimal("100000.00"), Decimal(0), None),
            ("1.1.2.2", Decimal("75000.00"), Decimal(0), None),
            ("3.1", Decimal(0), Decimal("225000.00"), None),
        ],
    },
    {
        "journal": "CSH",
        "entry_number": "202601-0002",
        "sequence_number": 2,
        "entry_date": date(2026, 1, 15),
        "reference": "EXP-1005",
        "narration": "شراء أدوات مكتبية نقدًا",
        "state": "draft",
        "lines": [
            ("5.1.3", Decimal("3500.00"), Decimal(0), "CC-01"),
            ("1.1.1", Decimal(0), Decimal("3500.00"), None),
        ],
    },
    {
        "journal": "CSH",
        "entry_number": "202601-0003",
        "sequence_number": 3,
        "entry_date": date(2026, 1, 28),
        "reference": "PAY-2026-01",
        "narration": "صرف رواتب الموظفين",
        "state": "in_review",
        "lines": [
            ("5.1.1", Decimal("40000.00"), Decimal(0), "CC-01"),
            ("2.1.2", Decimal(0), Decimal("40000.00"), None),
        ],
    },
    {
        "journal": "BNK",
        "entry_number": "202601-0004",
        "sequence_number": 4,
        "entry_date": date(2026, 2, 5),
        "reference": "PO-2026-001",
        "narration": "سداد مستحق مورد",
        "state": "in_review",
        "lines": [
            ("2.1.1", Decimal("25000.00"), Decimal(0), None),
            ("1.1.2.1", Decimal(0), Decimal("25000.00"), None),
        ],
    },
    {
        "journal": "BNK",
        "entry_number": "202601-0005",
        "sequence_number": 5,
        "entry_date": date(2026, 2, 10),
        "reference": "RENT-2026-02",
        "narration": "سداد إيجار المكتب",
        "state": "posted",
        "lines": [
            ("5.1.2", Decimal("12000.00"), Decimal(0), "CC-02"),
            ("1.1.2.2", Decimal(0), Decimal("12000.00"), None),
        ],
    },
    {
        "journal": "SAL",
        "entry_number": "202601-0006",
        "sequence_number": 6,
        "entry_date": date(2026, 2, 15),
        "reference": "INV-2026-010",
        "narration": "تحصيل إيرادات مشروع",
        "state": "posted",
        "lines": [
            ("1.1.2.1", Decimal("80000.00"), Decimal(0), "CC-01"),
            ("4.1.1", Decimal(0), Decimal("80000.00"), None),
        ],
    },
    {
        "journal": "PUR",
        "entry_number": "202601-0007",
        "sequence_number": 7,
        "entry_date": date(2026, 2, 20),
        "reference": "PO-2026-002",
        "narration": "شراء أثاث وتجهيزات",
        "state": "draft",
        "lines": [
            ("1.2.1", Decimal("30000.00"), Decimal(0), None),
            ("2.1.1", Decimal(0), Decimal("30000.00"), None),
        ],
    },
]


def _account(db, code: str) -> Account:
    """يجلب حساباً من شجرة الحسابات برمزه."""
    account = db.scalar(select(Account).where(Account.code == code))
    if account is None:
        raise RuntimeError(f"الحساب غير موجود في شجرة الحسابات: {code}")
    return account


def seed_cost_centers(db) -> int:
    """ينشئ مراكز التكلفة التجريبية إن لم تكن موجودة."""
    created = 0
    existing = {c.code for c in db.scalars(select(CostCenter)).all()}
    for code, name in DEMO_COST_CENTERS:
        if code in existing:
            continue
        db.add(CostCenter(code=code, name=name))
        created += 1
    db.commit()
    return created


def seed_demo_fiscal_year(db) -> FiscalYear:
    """ينشئ السنة المالية 2026 وفتراتها الشهرية إن لم تكن موجودة."""
    fy = db.scalar(select(FiscalYear).where(FiscalYear.name == "2026"))
    if fy is None:
        fy = FiscalYear(
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        db.add(fy)
        db.flush()

    existing_names = {p.name for p in fy.periods}
    for index, month_name in enumerate(MONTH_NAMES_AR, start=1):
        period_name = f"{month_name} 2026"
        if period_name in existing_names:
            continue
        start = date(2026, index, 1)
        # آخر يوم في الشهر: أول الشهر التالي ناقص يوم
        nxt = start.replace(day=28) + timedelta(days=4)
        end = nxt - timedelta(days=nxt.day)
        db.add(
            Period(
                fiscal_year_id=fy.id,
                name=period_name,
                start_date=start,
                end_date=end,
            )
        )
    db.commit()
    return fy


def seed_demo_entries(db, admin: User, fy: FiscalYear, cost_centers: dict) -> int:
    """ينشئ القيود التجريبية المتوازنة إن لم تكن موجودة."""
    existing = {e.entry_number for e in db.scalars(select(JournalEntry)).all()}
    journals = {j.code: j for j in db.scalars(select(Journal)).all()}
    accounts = {a.code: a for a in db.scalars(select(Account)).all()}
    created = 0

    for spec in DEMO_ENTRIES:
        if spec["entry_number"] in existing:
            continue

        journal = journals.get(spec["journal"])
        if journal is None:
            raise RuntimeError(f"الدفتر غير موجود: {spec['journal']}")

        amounts = [line[1] for line in spec["lines"]]
        total = sum(amounts)
        entry = JournalEntry(
            entry_number=spec["entry_number"],
            sequence_number=spec["sequence_number"],
            journal_id=journal.id,
            fiscal_year_id=fy.id,
            entry_date=spec["entry_date"],
            reference=spec["reference"],
            narration=spec["narration"],
            state=spec["state"],
            amount=total,
            created_by=admin.id,
        )

        posted = spec["state"] == "posted"
        for account_code, debit, credit, cc_code in spec["lines"]:
            account = accounts.get(account_code)
            if account is None:
                raise RuntimeError(f"الحساب غير موجود في شجرة الحسابات: {account_code}")
            cc = cost_centers.get(cc_code) if cc_code else None
            entry.lines.append(
                MoveLine(
                    account_id=account.id,
                    debit=debit,
                    credit=credit,
                    name=account.name,
                    cost_center_id=cc.id if cc else None,
                )
            )

        if posted:
            entry.posted_by = admin.id
            entry.posted_at = datetime(
                spec["entry_date"].year,
                spec["entry_date"].month,
                spec["entry_date"].day,
                hour=12,
                tzinfo=timezone.utc,
            )

        db.add(entry)
        created += 1

    db.commit()
    return created


def main() -> None:
    db = SessionLocal()
    try:
        cc_created = seed_cost_centers(db)
        fy = seed_demo_fiscal_year(db)

        admin = db.scalar(select(User).where(User.is_superuser == True))
        if admin is None:
            admin = db.scalars(select(User)).first()
        if admin is None:
            print("[demo] لا يوجد مستخدم — شغّل app/seed.py أولاً")
            return

        cost_centers = {c.code: c for c in db.scalars(select(CostCenter)).all()}
        entries_created = seed_demo_entries(db, admin, fy, cost_centers)

        print(f"[demo] cost centers created: {cc_created}")
        print(f"[demo] fiscal year: {fy.name}")
        print(f"[demo] journal entries created: {entries_created}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
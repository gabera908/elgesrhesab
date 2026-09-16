"""الإعدادات — المؤسسة، النسخ الاحتياطي، التصفير، الرصيد الافتتاحي."""
import io
import os
import subprocess
import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user, require_permission
from app.database import get_db
from app.models.account import Account
from app.models.journal import Journal, JournalEntry, MoveLine
from app.models.setting import Setting
from app.models.user import User

router = APIRouter(prefix="/api/settings", tags=["الإعدادات"])


class CompanySettings(BaseModel):
    name: str
    address: Optional[str] = None
    tax_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    currency: str = "EGP"
    fiscal_year_start_month: int = 1


class OpeningBalanceLine(BaseModel):
    account_id: uuid.UUID
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")


class OpeningBalanceRequest(BaseModel):
    journal_id: uuid.UUID
    entry_date: date
    narration: Optional[str] = "قيد الرصيد الافتتاحي"
    lines: List[OpeningBalanceLine]


# ===== إعدادات المؤسسة =====
@router.get("/company")
async def get_company_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.get(Setting, 1)
    if row is None:
        return {"name": settings.company_name, "currency": settings.company_currency}
    return {
        "name": row.name,
        "address": row.address,
        "tax_id": row.tax_id,
        "phone": row.phone,
        "email": row.email,
        "currency": row.currency,
        "fiscal_year_start_month": row.fiscal_year_start_month,
    }


@router.put("/company")
async def update_company_settings(
    payload: CompanySettings,
    current_user: User = Depends(require_permission("settings", "update")),
    db: Session = Depends(get_db),
):
    row = db.get(Setting, 1)
    if row is None:
        row = Setting(id=1, name=payload.name, currency=payload.currency)
        db.add(row)
    row.name = payload.name
    row.address = payload.address
    row.tax_id = payload.tax_id
    row.phone = payload.phone
    row.email = payload.email
    row.currency = payload.currency
    row.fiscal_year_start_month = payload.fiscal_year_start_month
    db.commit()
    return {"message": "تم حفظ الإعدادات"}


# ===== الرصيد الافتتاحي للبنوك والصناديق =====
@router.post("/opening-balance", status_code=status.HTTP_201_CREATED)
async def create_opening_balance(
    payload: OpeningBalanceRequest,
    current_user: User = Depends(require_permission("settings", "update")),
    db: Session = Depends(get_db),
):
    """إنشاء قيد الرصيد الافتتاحي للبنوك والصناديق."""
    journal = db.get(Journal, payload.journal_id)
    if journal is None:
        raise HTTPException(status_code=404, detail="الدفتر غير موجود")

    debit = sum(l.debit for l in payload.lines)
    credit = sum(l.credit for l in payload.lines)
    if debit != credit:
        raise HTTPException(status_code=422, detail=f"القيد غير متوازن: {debit} ≠ {credit}")

    entry = JournalEntry(
        entry_number=f"OPEN-{payload.entry_date.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
        journal_id=payload.journal_id,
        entry_date=payload.entry_date,
        reference="OPENING",
        narration=payload.narration,
        state="posted",
        amount=debit,
        created_by=current_user.id,
        posted_by=current_user.id,
    )
    db.add(entry)
    db.flush()
    for line in payload.lines:
        db.add(
            MoveLine(
                entry_id=entry.id,
                account_id=line.account_id,
                debit=line.debit,
                credit=line.credit,
                name="رصيد افتتاحي",
            )
        )
    db.commit()
    return {"message": "تم تسجيل الرصيد الافتتاحي", "entry_number": entry.entry_number}


# ===== النسخ الاحتياطي =====
BACKUP_DIR = "/app/backups"


@router.post("/backup")
async def create_backup(
    current_user: User = Depends(require_permission("settings", "update")),
    db: Session = Depends(get_db),
):
    """إنشاء نسخة احتياطية مشفَّرة من قاعدة البيانات."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    filename = f"backup-{date.today().isoformat()}.sql"
    filepath = os.path.join(BACKUP_DIR, filename)

    env = {
        **os.environ,
        "PGPASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
    }
    result = subprocess.run(
        [
            "pg_dump",
            "-h", "db",
            "-U", os.environ.get("POSTGRES_USER", "bridge_accounting"),
            "-d", os.environ.get("POSTGRES_DB", "accounting"),
            "-f", filepath,
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"فشل النسخ: {result.stderr}")

    # تشفير النسخة
    enc_path = filepath + ".enc"
    enc_result = subprocess.run(
        ["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-in", filepath, "-out", enc_path,
         "-pass", f"pass:{settings.backup_encryption_passphrase}"],
        capture_output=True,
        text=True,
    )
    if enc_result.returncode != 0:
        raise HTTPException(status_code=500, detail="فشل تشفير النسخة")
    os.remove(filepath)

    return {"message": "تم إنشاء نسخة احتياطية مشفَّرة", "filename": enc_path.split("/")[-1]}


# ===== تصفير الحسابات =====
class ResetRequest(BaseModel):
    confirmation: str  # يجب أن يكون "RESET"
    archive: bool = True


@router.post("/reset")
async def reset_accounts(
    payload: ResetRequest,
    current_user: User = Depends(require_permission("settings", "update")),
    db: Session = Depends(get_db),
):
    """تصفير الحسابات — يتطلب تأكيداً نصياً وأرشفة."""
    if payload.confirmation != "RESET":
        raise HTTPException(status_code=422, detail="تأكيد غير صحيح")

    # أرشفة الحركة قبل التصفير
    if payload.archive:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        archive_path = os.path.join(BACKUP_DIR, f"archive-before-reset-{date.today().isoformat()}.sql")
        env = {**os.environ, "PGPASSWORD": os.environ.get("POSTGRES_PASSWORD", "")}
        subprocess.run(
            ["pg_dump", "-h", "db",
             "-U", os.environ.get("POSTGRES_USER", "bridge_accounting"),
             "-d", os.environ.get("POSTGRES_DB", "accounting"),
             "-f", archive_path],
            capture_output=True, env=env,
        )

    db.execute(text("DELETE FROM move_lines"))
    db.execute(text("DELETE FROM journal_entries"))
    db.commit()
    return {"message": "تم تصفير الحسابات (القيود محذوفة، الحسابات محفوظة)"}

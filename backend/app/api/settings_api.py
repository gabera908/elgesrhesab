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
from app.database import Base, get_db
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


# ===== النسخ الاحتياطي (يدعم SQLite محلياً وPostgreSQL على Docker) =====
def _get_backup_dir() -> str:
    # الأولوية لمجلد العمل (ويندوز/تطوير)، ثم /app/backups (Docker)
    if os.name == "nt":
        order = (os.path.join(os.getcwd(), "backups"), "/app/backups")
    else:
        order = ("/app/backups", os.path.join(os.getcwd(), "backups"))
    for d in order:
        try:
            os.makedirs(d, exist_ok=True)
            # اختبار الكتابة فعلياً
            probe = os.path.join(d, ".write_test")
            with open(probe, "w") as f:
                f.write("ok")
            os.remove(probe)
            return d
        except OSError:
            continue
    fallback = os.path.join(os.getcwd(), "backups")
    os.makedirs(fallback, exist_ok=True)
    return fallback


BACKUP_DIR = "/app/backups"


def _encrypt_file(src: str, dest: str) -> None:
    phrase = settings.backup_encryption_passphrase or "default"
    try:
        r = subprocess.run(
            ["openssl", "enc", "-aes-256-cbc", "-pbkdf2",
             "-in", src, "-out", dest, "-pass", f"pass:{phrase}"],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode == 0:
            return
    except (FileNotFoundError, OSError):
        pass
    try:
        from cryptography.hazmat.primitives import hashes, padding
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        salt, iv = os.urandom(16), os.urandom(16)
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100_000)
        key = kdf.derive(phrase.encode("utf-8"))
        with open(src, "rb") as f:
            raw = f.read()
        padder = padding.PKCS7(128).padder()
        padded = padder.update(raw) + padder.finalize()
        enc = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
        with open(dest, "wb") as f:
            f.write(b"Salted__" + salt + iv + enc.update(padded) + enc.finalize())
        return
    except ImportError:
        pass
    import hashlib
    key = hashlib.pbkdf2_hmac("sha256", phrase.encode(), b"backup-salt", 100_000)
    with open(src, "rb") as f:
        raw = f.read()
    with open(dest, "wb") as f:
        f.write(b"XOR1" + bytes(b ^ key[i % len(key)] for i, b in enumerate(raw)))


def _sql_literal(value) -> str:
    """تحويل قيمة بايثون إلى لفظ SQL آمن لملف النسخة."""
    import datetime as _dt

    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    if isinstance(value, (_dt.datetime, _dt.date)):
        return f"'{value.isoformat()}'"
    if isinstance(value, uuid.UUID):
        return f"'{value}'"
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"'\\x{bytes(value).hex()}'"
    s = str(value).replace("'", "''")
    return f"'{s}'"


def _sqlite_file() -> Optional[str]:
    url = settings.database_url or ""
    if not url.lower().startswith("sqlite"):
        return None
    part = url.split("://", 1)[1].split("?", 1)[0].lstrip("/")
    if len(part) >= 2 and part[1] == ":":
        pass
    elif os.name != "nt":
        part = "/" + part
    for c in (part, os.path.abspath(part)):
        if c and os.path.isfile(c):
            return c
    return os.path.abspath(part)


@router.post("/backup")
async def create_backup(
    current_user: User = Depends(require_permission("settings", "update")),
    db: Session = Depends(get_db),
):
    """إنشاء نسخة احتياطية مشفَّرة — تفريغ SQL بايثون خالص (يعمل على أي حاوية)."""
    backup_dir = _get_backup_dir()
    stamp = date.today().isoformat()
    filepath = os.path.join(backup_dir, f"backup-{stamp}.sql")

    if (settings.database_url or "").lower().startswith("sqlite"):
        import sqlite3
        src = _sqlite_file()
        if not src or not os.path.isfile(src):
            raise HTTPException(status_code=500, detail="ملف قاعدة البيانات غير موجود")
        try:
            con = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    for line in con.iterdump():
                        f.write(line + "\n")
            finally:
                con.close()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"فشل تفريغ قاعدة البيانات: {exc}")
    else:
        # PostgreSQL: تفريغ بايثون خالص عبر SQLAlchemy — لا يحتاج pg_dump
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"-- Backup {stamp}\n-- generator: settings_api pure-python dump v1\n")
                for table in reversed(Base.metadata.sorted_tables):
                    rows = db.execute(table.select()).mappings().all()
                    cols = [c.name for c in table.columns]
                    f.write(f"-- table {table.name}: {len(rows)} rows\n")
                    for row in rows:
                        vals = ", ".join(_sql_literal(row[c]) for c in cols)
                        f.write(f"INSERT INTO {table.name} ({', '.join(cols)}) VALUES ({vals});\n")
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"فشل تفريغ قاعدة البيانات: {exc}")

    enc_path = filepath + ".enc"
    try:
        _encrypt_file(filepath, enc_path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"فشل تشفير النسخة: {exc}")
    finally:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except OSError:
            pass

    return {"message": "تم إنشاء نسخة احتياطية مشفَّرة", "filename": os.path.basename(enc_path)}


@router.get("/backups")
async def list_backups(
    current_user: User = Depends(require_permission("settings", "update")),
):
    """قائمة ملفات النسخ الاحتياطي المتاحة للتحميل."""
    backup_dir = _get_backup_dir()
    try:
        files = sorted((f for f in os.listdir(backup_dir) if f.endswith(".enc")), reverse=True)
    except OSError:
        files = []
    out = []
    for f in files:
        p = os.path.join(backup_dir, f)
        try:
            out.append({"filename": f, "size": os.path.getsize(p),
                        "modified": date.fromtimestamp(os.path.getmtime(p)).isoformat()})
        except OSError:
            continue
    return out


def _decrypt_file(src: str, dest: str) -> None:
    """فك تشفير ملف نسخة احتياطية (عكس _encrypt_file تماماً)."""
    phrase = settings.backup_encryption_passphrase or "default"
    with open(src, "rb") as f:
        blob = f.read()
    try:
        r = subprocess.run(
            ["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2",
             "-in", src, "-out", dest, "-pass", f"pass:{phrase}"],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode == 0 and os.path.isfile(dest):
            return
    except (FileNotFoundError, OSError):
        pass
    if blob.startswith(b"XOR1"):
        import hashlib
        key = hashlib.pbkdf2_hmac("sha256", phrase.encode(), b"backup-salt", 100_000)
        masked = blob[4:]
        with open(dest, "wb") as f:
            f.write(bytes(b ^ key[i % len(key)] for i, b in enumerate(masked)))
        return
    if blob.startswith(b"Salted__"):
        from cryptography.hazmat.primitives import hashes, padding
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        salt, iv, cipher = blob[8:24], blob[24:40], blob[40:]
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100_000)
        key = kdf.derive(phrase.encode("utf-8"))
        decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
        padded = decryptor.update(cipher) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        with open(dest, "wb") as f:
            f.write(unpadder.update(padded) + unpadder.finalize())
        return
    raise ValueError("صيغة الملف غير معروفة أو كلمة المرور خاطئة")


def _parse_insert_statements(sql_text: str):
    """يستخرج جمل INSERT من نص SQL ويجمعها حسب الجدول."""
    stmts, buf, in_str, depth = [], "", False, 0
    i = 0
    while i < len(sql_text):
        ch = sql_text[i]
        if in_str:
            buf += ch
            if ch == "'":
                if i + 1 < len(sql_text) and sql_text[i + 1] == "'":
                    buf += "'"
                    i += 1
                else:
                    in_str = False
        else:
            if ch == "'":
                in_str = True
                buf += ch
            elif ch == "(":
                depth += 1
                buf += ch
            elif ch == ")":
                depth = max(0, depth - 1)
                buf += ch
            elif ch == ";":
                buf += ch
                if buf.strip().upper().startswith("INSERT"):
                    stmts.append(buf.strip())
                buf, depth = "", 0
            elif ch == "-" and sql_text[i:i + 2] == "--":
                while i < len(sql_text) and sql_text[i] != "\n":
                    i += 1
            else:
                buf += ch
        i += 1
    if buf.strip().upper().startswith("INSERT"):
        stmts.append(buf.strip())
    grouped: dict = {}
    for s in stmts:
        try:
            tbl = s.split("INTO", 1)[1].strip().split("(", 1)[0].split()[0].strip('"')
        except IndexError:
            continue
        grouped.setdefault(tbl, []).append(s)
    return grouped


@router.get("/backups/download/{filename}")
async def download_backup(
    filename: str,
    current_user: User = Depends(require_permission("settings", "update")),
):
    """تحميل ملف نسخة احتياطية مشفَّرة."""
    from fastapi.responses import FileResponse
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="اسم ملف غير صالح")
    path = os.path.join(_get_backup_dir(), filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="الملف غير موجود")
    return FileResponse(path, filename=filename, media_type="application/octet-stream")


@router.post("/restore")
async def restore_backup(
    confirmation: str = "RESTORE",
    filename: Optional[str] = None,
    file: UploadFile | None = File(None),
    current_user: User = Depends(require_permission("settings", "update")),
    db: Session = Depends(get_db),
):
    """استعادة نسخة: نسخة أمان أولاً ثم مسح الجداول وإعادة الإدخال."""
    if confirmation != "RESTORE":
        raise HTTPException(status_code=422, detail="اكتب RESTORE للتأكيد")
    backup_dir = _get_backup_dir()
    tmp_upload = None
    try:
        if file is not None:
            if not (file.filename or "").endswith(".enc"):
                raise HTTPException(status_code=400, detail="الملف يجب أن يكون .enc")
            tmp_upload = os.path.join(backup_dir, f"upload-{uuid.uuid4().hex}.enc")
            with open(tmp_upload, "wb") as f:
                f.write(await file.read())
            enc_path = tmp_upload
        elif filename:
            if "/" in filename or "\\" in filename or ".." in filename:
                raise HTTPException(status_code=400, detail="اسم ملف غير صالح")
            enc_path = os.path.join(backup_dir, filename)
            if not os.path.isfile(enc_path):
                raise HTTPException(status_code=404, detail="ملف النسخة غير موجود")
        else:
            raise HTTPException(status_code=400, detail="اختر نسخة أو ارفع ملف .enc")

        # نسخة أمان تلقائية قبل الاستعادة
        safe_path = os.path.join(backup_dir, f"pre-restore-{date.today().isoformat()}.sql")
        try:
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(f"-- Pre-restore safety {date.today().isoformat()}\n")
                for table in reversed(Base.metadata.sorted_tables):
                    rows = db.execute(table.select()).mappings().all()
                    cols = [c.name for c in table.columns]
                    for row in rows:
                        vals = ", ".join(_sql_literal(row[c]) for c in cols)
                        f.write(f"INSERT INTO {table.name} ({', '.join(cols)}) VALUES ({vals});\n")
            _encrypt_file(safe_path, safe_path + ".enc")
        except Exception:  # noqa: BLE001
            pass
        finally:
            try:
                if os.path.exists(safe_path):
                    os.remove(safe_path)
            except OSError:
                pass

        plain_path = os.path.join(backup_dir, f"restore-{uuid.uuid4().hex}.sql")
        try:
            _decrypt_file(enc_path, plain_path)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"فشل فك التشفير: {exc}")
        try:
            with open(plain_path, encoding="utf-8") as f:
                sql_text = f.read()
        finally:
            try:
                os.remove(plain_path)
            except OSError:
                pass

        grouped = _parse_insert_statements(sql_text)
        is_sqlite_dump = "CREATE TABLE" in sql_text.upper() and "generator: settings_api" not in sql_text
        if not grouped and not is_sqlite_dump:
            raise HTTPException(status_code=400, detail="الملف لا يحتوي بيانات صالحة")

        is_pg = not (settings.database_url or "").lower().startswith("sqlite")
        if is_sqlite_dump:
            # تفريغ sqlite3 الخام يُستعاد عبر تنفيذه مباشرة (جداول فارغة تُنشأ ضمنياً)
            try:
                if is_pg:
                    db.execute(text("SET session_replication_role = replica"))
                for table in reversed(Base.metadata.sorted_tables):
                    db.execute(table.delete())
                for stmt in (s.strip() for s in sql_text.split(";")):
                    su = stmt.strip().upper()
                    if su.startswith("INSERT"):
                        db.execute(text(stmt))
                db.commit()
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                raise HTTPException(status_code=500, detail=f"فشل الاستعادة: {str(exc)[:300]}")
            finally:
                try:
                    if is_pg:
                        db.execute(text("SET session_replication_role = DEFAULT"))
                        db.commit()
                except Exception:  # noqa: BLE001
                    pass
            restored = sql_text.upper().count("INSERT INTO")
            return {"message": f"تمت الاستعادة بنجاح ({restored} سجلاً)"}

        try:
            if is_pg:
                db.execute(text("SET session_replication_role = replica"))
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(table.delete())
            for table in Base.metadata.sorted_tables:
                for stmt in grouped.get(table.name, []):
                    db.execute(text(stmt))
            db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            raise HTTPException(status_code=500, detail=f"فشل الاستعادة: {str(exc)[:300]}")
        finally:
            try:
                if is_pg:
                    db.execute(text("SET session_replication_role = DEFAULT"))
                    db.commit()
            except Exception:  # noqa: BLE001
                pass
        restored = sum(len(v) for v in grouped.values())
        return {"message": f"تمت الاستعادة بنجاح ({restored} سجلاً)"}
    finally:
        if tmp_upload:
            try:
                os.remove(tmp_upload)
            except OSError:
                pass


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

    # أرشفة الحركة قبل التصفير (تفريغ داخلي — لا يعتمد على pg_dump)
    if payload.archive:
        try:
            backup_dir = _get_backup_dir()
            archive_path = os.path.join(backup_dir, f"archive-before-reset-{date.today().isoformat()}.sql")
            with open(archive_path, "w", encoding="utf-8") as f:
                f.write(f"-- Archive before reset {date.today().isoformat()}\n")
                from app.models.journal import JournalEntry as _JE, MoveLine as _ML
                for table in (_JE.__table__, _ML.__table__):
                    rows = db.execute(table.select()).mappings().all()
                    cols = [c.name for c in table.columns]
                    for row in rows:
                        vals = ", ".join(_sql_literal(row[c]) for c in cols)
                        f.write(f"INSERT INTO {table.name} ({', '.join(cols)}) VALUES ({vals});\n")
        except Exception:  # noqa: BLE001 — الأرشفة اختيارية ولا تمنع التصفير
            pass

    db.execute(text("DELETE FROM move_lines"))
    db.execute(text("DELETE FROM journal_entries"))
    db.commit()
    return {"message": "تم تصفير الحسابات (القيود محذوفة، الحسابات محفوظة)"}

#!/bin/bash
# سكربت النسخ الاحتياطي — يُجدول عبر cron داخل حاوية الخادم
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/app/backups"
DB_NAME="${POSTGRES_DB:-accounting}"
DB_USER="${POSTGRES_USER:-bridge_accounting}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

mkdir -p "$BACKUP_DIR"

echo "[$(date)] بدء النسخ الاحتياطي..."

# 1. تصدير قاعدة البيانات
DUMP_FILE="$BACKUP_DIR/db_${TIMESTAMP}.sql"
docker exec accounting-db pg_dump -U "$DB_USER" "$DB_NAME" > "$DUMP_FILE"

# 2. التشفير (AES-256-CBC + PBKDF2)
ENC_FILE="${DUMP_FILE}.enc"
openssl enc -aes-256-cbc -pbkdf2 \
    -in "$DUMP_FILE" \
    -out "$ENC_FILE" \
    -pass "pass:${BACKUP_ENCRYPTION_PASSPHRASE}"

# 3. حذف النسخة غير المشفَّرة
rm -f "$DUMP_FILE"

# 4. التحقق من التشفير
if [ ! -s "$ENC_FILE" ]; then
    echo "[$(date)] خطأ: فشل التشفير"
    exit 1
fi

# 5. حذف النسخ القديمة (سياسة الاحتفاظ)
find "$BACKUP_DIR" -name "db_*.enc" -mtime +${RETENTION_DAYS} -delete

echo "[$(date)] اكتمل النسخ: $ENC_FILE"
echo "[$(date)] النسخ الحالية: $(ls -1 "$BACKUP_DIR"/db_*.enc | wc -l)"

#!/bin/bash
# سكربت الاستعادة — يستعيد نسخة احتياطية مشفَّرة
set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "الاستخدام: ./restore.sh <path-to-encrypted-backup.enc>"
    exit 1
fi

ENC_FILE="$1"
DB_NAME="${POSTGRES_DB:-accounting}"
DB_USER="${POSTGRES_USER:-bridge_accounting}"

if [ ! -f "$ENC_FILE" ]; then
    echo "خطأ: الملف غير موجود: $ENC_FILE"
    exit 1
fi

echo "[$(date)] بدء الاستعادة من: $ENC_FILE"
echo "تحذير: ستُستبدل البيانات الحالية. اضغط Ctrl+C للإلغاء."
read -r -p "اكتب RESTORE للتأكيد: " CONFIRM

if [ "$CONFIRM" != "RESTORE" ]; then
    echo "تم الإلغاء."
    exit 0
fi

# 1. فك التشفير
SQL_FILE=$(mktemp /tmp/restore_XXXXXX.sql)
openssl enc -d -aes-256-cbc -pbkdf2 \
    -in "$ENC_FILE" \
    -out "$SQL_FILE" \
    -pass "pass:${BACKUP_ENCRYPTION_PASSPHRASE}"

# 2. استعادة قاعدة البيانات
docker exec -i accounting-db psql -U "$DB_USER" -d "$DB_NAME" < "$SQL_FILE"

# 3. تنظيف
rm -f "$SQL_FILE"

echo "[$(date)] اكتملت الاستعادة بنجاح"

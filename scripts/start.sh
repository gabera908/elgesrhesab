#!/bin/bash
# سكربت الإقلاع — يهيئ الحاويات ويزرع البيانات الأولية
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== التحقق من ملف البيئة ==="
if [ ! -f .env ]; then
    echo "إنشاء .env من القالب..."
    cp .env.example .env
    echo "⚠️  عدّل القيم في .env قبل الإنتاج!"
fi

echo "=== بناء الحاويات ==="
docker compose build

echo "=== تشغيل الحاويات ==="
docker compose up -d

echo "=== انتظار جاهزية قاعدة البيانات ==="
until docker compose exec -T db pg_isready -U "${POSTGRES_USER:-bridge_accounting}" >/dev/null 2>&1; do
    sleep 2
done
echo "✓ قاعدة البيانات جاهزة"

echo "=== زرع الأدوار الأولية ==="
docker compose exec -T backend python -m app.seed

echo ""
echo "=== تم! ==="
echo "الواجهة:  http://localhost"
echo "الخادم:   http://localhost/health"
echo "السجلات:  docker compose logs -f"

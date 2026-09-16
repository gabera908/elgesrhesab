#!/bin/bash
# سكربت النشر على خادم Docker البعيد
# الاستخدام: ./deploy.sh user@remote-host [branch]
# المتطلبات على الخادم البعيد: Docker, Docker Compose, envsubst (gettext)

set -euo pipefail

REMOTE_HOST="${1:-}"
BRANCH="${2:-main}"

if [ -z "$REMOTE_HOST" ]; then
    echo "الاستخدام: $0 user@host [branch]"
    exit 1
fi

# التحقق من وجود .env.production محلياً
if [ ! -f .env.production ]; then
    echo "❌ ملف .env.production غير موجود. انسخ .env.production.example وعدل القيم."
    exit 1
fi

echo "=== بدء النشر على $REMOTE_HOST ==="
echo "الفرع: $BRANCH"

# 1. نسخ الملفات للخادم
echo "📦 نسخ الكود..."
rsync -avz --delete \
    --exclude '.git' \
    --exclude 'node_modules' \
    --exclude 'dist' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'backups' \
    --exclude '*.enc' \
    --exclude '.env' \
    --exclude '.env.*' \
    --exclude '*.sql' \
    --exclude '*.sql.gz' \
    . "$REMOTE_HOST:/opt/accounting/"

# 2. نسخ ملف البيئة
echo "🔐 نسخ ملف البيئة..."
scp .env.production "$REMOTE_HOST:/opt/accounting/.env.production"

# 3. تنفيذ النشر على الخادم البعيد
echo "🚀 تنفيذ النشر على الخادم..."
ssh "$REMOTE_HOST" << 'ENDSSH'
set -euo pipefail
cd /opt/accounting

# تحميل متغيرات البيئة
set -a
source .env.production
set +a

# إنشاء prod.conf مع استبدال المتغيرات
envsubst '\${HOST_DOMAIN}' < nginx/conf.d/prod.conf > nginx/conf.d/prod.conf.tmp
mv nginx/conf.d/prod.conf.tmp nginx/conf.d/prod.conf

# تسجيل الدخول لـ Docker Hub إن لزم
# docker login

# بناء وتشغيل
echo "🔨 بناء الحاويات..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml build --pull

echo "🔄 إعادة تشغيل الخدمات..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --remove-orphans

# انتظار جاهزية قاعدة البيانات
echo "⏳ انتظار قاعدة البيانات..."
until docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
    sleep 2
done

# زرع البيانات الأولية (في أول مرة فقط)
if ! docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T backend python -c "from app.database import SessionLocal; from app.models.user import User; db=SessionLocal(); print('seeded' if db.query(User).count() else 'empty'); db.close()" 2>/dev/null | grep -q seeded; then
    echo "🌱 زرع البيانات الأولية..."
    docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T backend python -m app.seed_accounts
fi

# تنظيف الصور القديمة
docker image prune -f

echo "✅ اكتمل النشر!"
echo "🌐 النظام متاح على: https://$HOST_DOMAIN"

ENDSSH

echo ""
echo "=== النشر مكتمل ==="
echo "🔗 https://$HOST_DOMAIN"
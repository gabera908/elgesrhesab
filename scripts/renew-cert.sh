#!/bin/bash
# تجديد شهادة Let's Encrypt تلقائياً — يُضاف إلى cron
# 0 3 * * * /opt/accounting/scripts/renew-cert.sh >> /var/log/cert-renewal.log 2>&1

set -euo pipefail

cd /opt/accounting

# تحميل المتغيرات
set -a
source .env.production
set +a

DOMAIN="$HOST_DOMAIN"
EMAIL="admin@$DOMAIN"

echo "[$(date)] بدء تجديد الشهادة لـ $DOMAIN"

# تجديد الشهادة
docker run --rm \
    -v "/opt/accounting/certdata:/etc/letsencrypt" \
    -v "/opt/accounting/certdata:/var/lib/letsencrypt" \
    certbot/certbot renew \
    --webroot -w /var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --quiet

# إعادة تحميل nginx
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec nginx nginx -s reload

echo "[$(date)] اكتمل تجديد الشهادة"
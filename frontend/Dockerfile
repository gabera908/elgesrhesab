FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps

COPY . .

ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# مرحلة الإنتاج — Nginx يقدّم الملفات الثابتة
FROM nginx:1.27-alpine

# نستخدم مستخدم nginx المدمج في الصورة (موجود مسبقاً وغير جذري)

COPY --from=builder /app/dist /usr/share/nginx/html

# إعدادات SPA — كل المسارات تذهب لـ index.html
RUN echo 'server { \
    listen 80; \
    server_name _; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
    location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ { \
        expires 1y; \
        add_header Cache-Control "public, immutable"; \
    } \
}' > /etc/nginx/conf.d/default.conf

# ملاحظة: يعمل كـ root مثل حاوية nginx الرئيسية (شبكة داخلية فقط)
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=15s \
  CMD wget --spider -q http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]

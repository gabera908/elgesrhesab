FROM python:3.12-slim

# مستخدم غير جذري للإنتاج
RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

WORKDIR /app

# تثبيت التبعيات أولاً للاستفادة من التخزين المؤقت للطبقات
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# إنشاء المجلدات ومنح الملكية
RUN mkdir -p /app/attachments /app/backups && chown -R app:app /app

USER app

EXPOSE 8010

HEALTHCHECK --interval=15s --timeout=5s --retries=5 --start-period=30s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8010/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010", "--workers", "4", "--proxy-headers"]

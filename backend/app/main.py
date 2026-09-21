"""نقطة دخول تطبيق FastAPI — الجسر المصري للإعلام والتنمية."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.api import api_router
from app.api.auth import limiter as auth_limiter
from app.config import settings
from app.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """دورة حياة التطبيق — إنشاء الجداول (idempotent) في كل بيئة."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="نظام الحسابات — الجسر المصري للإعلام والتنمية",
    description="نظام محاسبة مؤسسي بالقيد المزدوج",
    version="1.0.0",
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)

# Rate limiting — يعمل خلف Nginx عبر X-Forwarded-For
app.state.limiter = auth_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — أصول مسموحة فقط
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    """ترويسات الأمان الأساسية (CSP/X-Frame/X-Content-Type)."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = (
        "max-age=63072000; includeSubDomains; preload"
    )
    return response


@app.get("/health")
async def health():
    return JSONResponse({"status": "healthy", "service": "accounting-backend"})


@app.get("/")
async def root():
    return JSONResponse(
        {
            "name": "نظام الحسابات — الجسر المصري للإعلام والتنمية",
            "version": "1.0.0",
        }
    )


app.include_router(api_router)

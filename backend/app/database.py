"""اتصال قاعدة البيانات مع إدارة الجلسات."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

from app.config import settings

_engine_kwargs: dict = {"pool_pre_ping": True, "echo": False}
if (settings.database_url or "").lower().startswith("sqlite"):
    _engine_kwargs["poolclass"] = NullPool
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs.update({"pool_size": 10, "max_overflow": 20, "pool_recycle": 3600})

engine = create_engine(settings.database_url, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """يعتمد على حقن الجلسة في مسارات FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

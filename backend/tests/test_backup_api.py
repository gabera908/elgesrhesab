"""اختبارات تكامل: backup → list → restore عبر API على SQLite مؤقتة."""
import io
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 — تسجيل كل الجداول في Base.metadata
from app.api import settings_api
from app.database import Base, get_db


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    # قاعدة SQLite حقيقية على القرص (iterdump يحتاج ملفاً)
    engine = create_engine(f"sqlite:///{db_file}")
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    # توجيه الوحدة للملف المؤقت ومجلد النسخ المؤقت
    monkeypatch.setattr(settings_api.settings, "database_url", f"sqlite:///{db_file}")
    monkeypatch.setattr(settings_api, "_get_backup_dir", lambda: str(tmp_path))
    monkeypatch.setattr(settings_api, "_sqlite_file", lambda: str(db_file))

    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    from app.main import app

    app.dependency_overrides[get_db] = override_db

    # تجاوز المصادقة والصلاحيات: require_permission يعتمد على get_current_user،
    # فنستبدل get_current_user بمستخدم وهمي بصلاحية كاملة.
    from app.core.deps import get_current_user

    async def fake_user():
        class U:
            id = "test"
            is_superuser = True

        return U()

    app.dependency_overrides[get_current_user] = fake_user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_backup_list_roundtrip(client):
    r = client.post("/api/settings/backup")
    assert r.status_code == 200, r.text
    filename = r.json()["filename"]
    assert filename.endswith(".enc")

    r = client.get("/api/settings/backups")
    assert r.status_code == 200
    assert any(b["filename"] == filename for b in r.json())

    # تحميل النسخة
    r = client.get(f"/api/settings/backups/download/{filename}")
    assert r.status_code == 200
    assert len(r.content) > 0


def test_restore_roundtrip_with_seeded_data(client, tmp_path):
    """زرع دور + مستخدم، ثم backup → حذف الكل → restore يعيد الصفوف."""
    import uuid

    from sqlalchemy import create_engine as _ce
    from sqlalchemy.orm import sessionmaker as _sm

    from app.models.rbac import Role
    from app.models.user import User

    eng = _ce(f"sqlite:///{tmp_path}/test.db")
    S = _sm(bind=eng)
    s = S()
    role = Role(id=uuid.uuid4(), name="admin", description="t", is_system=True)
    s.add(role)
    s.flush()
    s.add(User(full_name="Seed User", email="seed@x.io", username="seeduser",
               password_hash="x", role_id=role.id))
    s.commit()
    s.close()

    r = client.post("/api/settings/backup")
    assert r.status_code == 200, r.text
    filename = r.json()["filename"]

    r = client.post("/api/settings/restore",
                    params={"confirmation": "RESTORE", "filename": filename})
    assert r.status_code == 200, r.text
    assert "تمت الاستعادة بنجاح" in r.json()["message"]
    assert "(2 " in r.json()["message"]  # صفّان: الدور + المستخدم

    # نسخة أمان pre-restore تُنشأ تلقائياً
    r = client.get("/api/settings/backups")
    assert any(b["filename"].startswith("pre-restore-") for b in r.json())


def test_restore_requires_confirmation(client):
    r = client.post("/api/settings/restore", params={"confirmation": "WRONG"})
    assert r.status_code == 422


def test_restore_missing_file(client):
    r = client.post(
        "/api/settings/restore",
        params={"confirmation": "RESTORE", "filename": "nope.sql.enc"},
    )
    assert r.status_code == 404


def test_restore_upload_enc(client, tmp_path):
    """رفع .enc حقيقي (من نسخة مزروعة) يُستعاد بنجاح."""
    import uuid

    from sqlalchemy import create_engine as _ce
    from sqlalchemy.orm import sessionmaker as _sm

    from app.models.rbac import Role

    eng = _ce(f"sqlite:///{tmp_path}/test.db")
    S = _sm(bind=eng)
    s = S()
    s.add(Role(id=uuid.uuid4(), name="viewer", description="t", is_system=True))
    s.commit()
    s.close()

    r = client.post("/api/settings/backup")
    filename = r.json()["filename"]
    r = client.get(f"/api/settings/backups/download/{filename}")
    files = {"file": (filename, io.BytesIO(r.content), "application/octet-stream")}
    r = client.post("/api/settings/restore", params={"confirmation": "RESTORE"}, files=files)
    assert r.status_code == 200, r.text


def test_restore_rejects_plain_sql_upload(client):
    files = {"file": ("evil.sql", io.BytesIO(b"DROP TABLE users;"), "text/plain")}
    r = client.post("/api/settings/restore", params={"confirmation": "RESTORE"}, files=files)
    assert r.status_code == 400

"""تهيئة pytest للباك-إند — SQLite بالذاكرة + تجاوز إعدادات البيئة."""
import os
import sys

os.environ.setdefault("SECRET_KEY", "test_secret_key_0123456789_abcdef_0123456789")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("BACKUP_ENCRYPTION_PASSPHRASE", "test-passphrase")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

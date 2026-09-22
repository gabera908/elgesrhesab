"""اختبارات pure-function لوحدة النسخ الاحتياطي: تشفير/فك، SQL literals، محلل INSERT."""
import datetime as dt
import uuid
from decimal import Decimal

from app.api.settings_api import (
    _decrypt_file,
    _encrypt_file,
    _parse_insert_statements,
    _sql_literal,
)


def test_sql_literal_types():
    assert _sql_literal(None) == "NULL"
    assert _sql_literal(True) == "TRUE"
    assert _sql_literal(False) == "FALSE"
    assert _sql_literal(5) == "5"
    assert _sql_literal(Decimal("10.5")) == "10.5"
    assert _sql_literal(dt.date(2026, 1, 2)) == "'2026-01-02'"
    uid = uuid.uuid4()
    assert _sql_literal(uid) == f"'{uid}'"
    # هروب علامة الاقتباس — يمنع كسر جملة INSERT
    assert _sql_literal("it's") == "'it''s'"


def test_encrypt_decrypt_roundtrip_openssl(tmp_path):
    """المسار الأساسي على السيرفر (openssl متاح)."""
    src = tmp_path / "plain.sql"
    enc = tmp_path / "plain.sql.enc"
    out = tmp_path / "restored.sql"
    src.write_text("-- Backup\nINSERT INTO users (id, name) VALUES ('1', 'a;b');\n", encoding="utf-8")
    _encrypt_file(str(src), str(enc))
    assert enc.stat().st_size > 0
    _decrypt_file(str(enc), str(out))
    assert out.read_text(encoding="utf-8") == src.read_text(encoding="utf-8")


def test_decrypt_xor_legacy_format(tmp_path):
    """صيغة XOR1 القديمة تُفك بدون openssl."""
    import hashlib

    phrase = "test-passphrase"
    key = hashlib.pbkdf2_hmac("sha256", phrase.encode(), b"backup-salt", 100_000)
    raw = b"hello backup"
    enc = tmp_path / "legacy.enc"
    out = tmp_path / "legacy.sql"
    enc.write_bytes(b"XOR1" + bytes(b ^ key[i % len(key)] for i, b in enumerate(raw)))
    _decrypt_file(str(enc), str(out))
    assert out.read_bytes() == raw


def test_parse_inserts_multiline_and_quotes():
    sql = (
        "-- comment line\n"
        "INSERT INTO users (id, name) VALUES ('1', 'a;b');\n"
        "INSERT INTO users (id, name) VALUES\n('2', 'it''s');\n"
        "CREATE TABLE x (id int);\n"
    )
    grouped = _parse_insert_statements(sql)
    assert set(grouped) == {"users"}
    assert len(grouped["users"]) == 2
    assert "a;b" in grouped["users"][0]
    assert "it''s" in grouped["users"][1]


def test_parse_inserts_empty():
    assert _parse_insert_statements("-- nothing here\nCREATE TABLE x (id int);") == {}

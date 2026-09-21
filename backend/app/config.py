"""إعدادات التطبيق — تُقرأ من متغيرات البيئة بمصادقة صارمة."""
from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    # البنية التحتية
    environment: str = "development"
    secret_key: str
    database_url: str
    redis_url: str

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7

    # الأمان
    allowed_origins: str = ""
    login_rate_limit_per_minute: int = 5
    api_rate_limit_per_minute: int = 120
    twofa_issuer: str = "الجسر المصري للإعلام والتنمية"
    backup_encryption_passphrase: str = "default"

    # كوكيز المصادقة: None = تلقائي (Secure فقط على HTTPS)
    # اضبطها false عند التشغيل على HTTP داخل الشبكة المحلية، وtrue إجبارياً في الإنتاج العام.
    cookie_secure: Optional[bool] = None

    # المؤسسة
    company_name: str = "الجسر المصري للإعلام والتنمية"
    company_currency: str = "EGP"
    company_fiscal_year_start_month: int = 1

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

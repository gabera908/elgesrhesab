"""تهيئة النظام — زرع الأدوار والمستخدم الأول."""
import uuid

from sqlalchemy import select

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.rbac import Permission, Role
from app.models.user import User

# الأدوار الافتراضية مع صلاحياتها
ROLE_PERMISSIONS = {
    "admin": {
        "accounts": ["read", "create", "update", "delete"],
        "journals": ["read", "create", "update", "post", "cancel"],
        "partners": ["read", "create", "update", "delete"],
        "reports": ["read"],
        "settings": ["read", "update"],
    },
    "accountant": {
        "accounts": ["read"],
        "journals": ["read", "create", "update"],
        "partners": ["read", "create", "update"],
        "reports": ["read"],
        "settings": ["read"],
    },
    "reviewer": {
        "accounts": ["read"],
        "journals": ["read", "post", "cancel"],
        "partners": ["read"],
        "reports": ["read"],
        "settings": ["read"],
    },
    "viewer": {
        "accounts": ["read"],
        "journals": ["read"],
        "partners": ["read"],
        "reports": ["read"],
        "settings": ["read"],
    },
}


def seed_roles(db) -> None:
    """ينشئ الأدوار الأربعة وصلاحياتها."""
    for role_name, perms in ROLE_PERMISSIONS.items():
        role = db.scalar(select(Role).where(Role.name == role_name))
        if role is None:
            role = Role(
                name=role_name,
                description={
                    "admin": "مدير النظام — كامل الصلاحيات",
                    "accountant": "محاسب — إنشاء القيود",
                    "reviewer": "مراجع — ترحيل وإلغاء القيود",
                    "viewer": "مشاهد — قراءة فقط",
                }[role_name],
                is_system=True,
            )
            db.add(role)
            db.flush()
        existing = {(p.module, p.action) for p in role.permissions}
        for module, actions in perms.items():
            for action in actions:
                if (module, action) not in existing:
                    db.add(Permission(role_id=role.id, module=module, action=action))
    db.commit()


def create_admin(db, email: str, password: str, full_name: str = "مدير النظام") -> User:
    """ينشئ أول مدير أعلى."""
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        return existing

    role = db.scalar(select(Role).where(Role.name == "admin"))
    user = User(
        full_name=full_name,
        email=email,
        username=email.split("@")[0],
        password_hash=hash_password(password),
        role_id=role.id if role else None,
        is_superuser=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_roles(db)
        admin_email = "admin@bridge-media.org"
        admin = create_admin(db, admin_email, "Admin@12345678")
        print(f"Admin created: {admin.email}")
    finally:
        db.close()

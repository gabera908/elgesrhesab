"""المرفقات — ملفات مرتبطة بالقيود اليومية."""
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.journal import JournalEntry

# الأنواع المسموحة (قائمة بيضاء)
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
    "application/vnd.ms-excel",  # xls
    "text/csv",
}

# الحد الأقصى: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024


class Attachment(Base, TimestampMixin):
    """ملف مرفق بقيد يومي."""

    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column()

    entry: Mapped["JournalEntry"] = relationship(back_populates="attachments")

    def __repr__(self) -> str:
        return f"<Attachment {self.filename}>"

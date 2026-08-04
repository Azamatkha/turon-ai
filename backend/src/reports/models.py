from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base import Base
from src.core.database.mixins import TimestampMixin, UUIDIDMixin
from src.reports.enums import ReportStatus


class UserReport(Base, UUIDIDMixin, TimestampMixin):
    """Foydalanuvchi murojaati — muammo haqida xabar yoki taklif."""

    __tablename__ = "user_reports"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    # ReportKind: "problem" | "suggestion"
    kind: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    # MEDIA_ROOT'ga nisbatan yo'l, masalan "reports/2026/08/<uuid>.png".
    # Fayl statik mount orqali emas, huquq tekshiriladigan endpoint orqali beriladi.
    screenshot_path: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None
    )
    # ReportStatus: "new" | "in_progress" | "resolved"
    status: Mapped[str] = mapped_column(
        String(16),
        default=ReportStatus.NEW.value,
        server_default=ReportStatus.NEW.value,
        index=True,
    )
    admin_comment: Mapped[str] = mapped_column(Text, default="", server_default="")
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

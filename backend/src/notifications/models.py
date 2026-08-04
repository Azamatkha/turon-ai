from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base import Base
from src.core.database.mixins import TimestampMixin, UUIDIDMixin


class Notification(Base, UUIDIDMixin, TimestampMixin):
    """Bitta foydalanuvchiga tegishli bildirishnoma.

    Xabar matni bazada saqlanmaydi: `type` + `params` saqlanadi va matn
    frontendda foydalanuvchi tiliga o'giriladi. Aks holda xabar yozilgan
    tilda qotib qolardi (interfeys 3 tilda ishlaydi).
    """

    __tablename__ = "notifications"
    __table_args__ = (
        # Ro'yxat so'rovi: bitta foydalanuvchining yangilaridan eskisiga
        Index("ix_notifications_user_id_created_at", "user_id", "created_at"),
        # Eng issiq so'rov — har 30 soniyada o'qilmaganlar sonini olish.
        # Partial indeks bo'lgani uchun o'qilganlar unga umuman kirmaydi.
        Index(
            "ix_notifications_unread",
            "user_id",
            postgresql_where=text("is_read = false"),
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    # NotificationType qiymatlaridan biri
    type: Mapped[str] = mapped_column(String(32))
    # Matnga qo'yiladigan qiymatlar, masalan {"title": "Kredit siyosati"}
    params: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    # Bog'liq obyekt id'si (masalan murojaat) — frontendda ochish uchun
    entity_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, default=None
    )

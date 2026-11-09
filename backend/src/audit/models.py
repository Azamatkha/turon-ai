from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base import Base
from src.core.database.mixins import TimestampMixin, UUIDIDMixin


class AuditLog(Base, UUIDIDMixin, TimestampMixin):
    """Admin amali: kim, nima qildi, nimaga, qachon.

    Faqat yoziladi — yangilanmaydi va o'chirilmaydi. Amalni bajargan user
    keyin o'chirilsa ham yozuv qoladi (`actor_username` — o'sha paytdagi nusxa).
    """

    __tablename__ = "audit_logs"

    actor_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_username: Mapped[str] = mapped_column(String(60))
    # Masalan: "user.update", "knowledge.delete" (qara: src/audit/actions.py)
    action: Mapped[str] = mapped_column(String(50), index=True)
    # "user" | "knowledge" | "report" | "guide" | "message"
    target_type: Mapped[str] = mapped_column(String(30), index=True)
    target_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Odam o'qiydigan nom: login, hujjat sarlavhasi va hokazo
    target_label: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # O'zgargan maydonlar va qo'shimcha ma'lumot (parollar HECH QACHON yozilmaydi)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)

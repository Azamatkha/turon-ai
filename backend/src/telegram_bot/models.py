"""Telegram yordam boti (aihelp) ma'lumotlarining nusxasi.

Bot alohida noutbukda o'z bazasi bilan ishlaydi va shu jadvallarga davriy
ravishda push qiladi (`POST /v1/telegram-bot/sync`). Bu yerda faqat o'qish uchun
saqlanadi — haqiqiy manba botning o'z bazasi. Sayt userlariga bog'lanmaydi.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base import Base
from src.core.database.mixins import TimestampMixin, UUIDIDMixin


class TelegramBotUser(Base, UUIDIDMixin, TimestampMixin):
    """Botdan foydalangan Telegram user."""

    __tablename__ = "telegram_bot_users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str] = mapped_column(String(64), default="", server_default="")
    full_name: Mapped[str] = mapped_column(String(256), default="", server_default="")
    # uz | ru | en (ro'yxatdan o'tmagan bo'lsa bo'sh)
    language: Mapped[str] = mapped_column(String(8), default="", server_default="")
    phone: Mapped[str] = mapped_column(String(32), default="", server_default="")
    # lang | phone | done
    reg_step: Mapped[str] = mapped_column(String(8), default="", server_default="")
    is_banned: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    # Botga birinchi kirgan vaqti (botdagi created_at)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, index=True
    )


class TelegramBotMessage(Base, UUIDIDMixin, TimestampMixin):
    """Userning murojaati yoki adminning javobi."""

    __tablename__ = "telegram_bot_messages"

    # Botdagi xabar ID si — qayta sync bo'lganda shu bo'yicha yangilanadi
    bot_message_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("telegram_bot_users.id", ondelete="CASCADE"),
        index=True,
    )
    # in — userdan, out — admin javobi
    direction: Mapped[str] = mapped_column(String(8))
    # new | answered | closed | sent | failed
    status: Mapped[str] = mapped_column(String(16))
    # text, photo, video, voice, document, album ...
    content_type: Mapped[str] = mapped_column(String(32), default="text")
    items: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    text: Mapped[str] = mapped_column(Text, default="", server_default="")
    admin_name: Mapped[str] = mapped_column(String(128), default="", server_default="")
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    answered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

from uuid import UUID

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base import Base
from src.core.database.mixins import SoftDeleteMixin, TimestampMixin, UUIDIDMixin


class ChatSession(Base, UUIDIDMixin, TimestampMixin, SoftDeleteMixin):
    """Bitta suhbat (chat). Har bir foydalanuvchining o'z suhbatlari bo'ladi."""

    __tablename__ = "chat_sessions"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), default="")
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # Tarjimon rejimi holati (sessiyaga bog'langan — veb ham, mobil ham shu
    # yerdan o'qiydi): None — o'chiq; "pending" — /translate yozildi, til
    # kutilmoqda; "en" | "ru" | "uz" | "uz_cyrl" — shu tilga tarjima qilinadi.
    translate_lang: Mapped[str | None] = mapped_column(String(10), nullable=True)


class ChatMessage(Base, UUIDIDMixin, TimestampMixin):
    """Suhbat ichidagi bitta xabar. role = 'user' yoki 'assistant'."""

    __tablename__ = "chat_messages"

    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    # Foydalanuvchi bahosi: "up" | "down" | None
    vote: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Dislike sababi: "wrong" | "outdated" | "incomplete" | "other" va ixtiyoriy
    # izoh. Faqat vote="down" bo'lganda to'ldiriladi — admin ko'rib chiqadi.
    vote_reason: Mapped[str | None] = mapped_column(String(20), nullable=True)
    vote_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Admin "Yoqmagan javoblar" ro'yxatida ko'rib chiqdi deb belgilagan
    vote_reviewed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    # Assistant javobiga ketgan tokenlar (router + javob) va to'xtash sababi.
    # Ilgari saqlanmasdi: sahifa yangilanganda token hisoblagichi barcha eski
    # javoblardan yo'qolardi. Foydalanuvchi xabarida va eski yozuvlarda NULL.
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    finish_reason: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Javob tayangan bilim bazasi hujjatlari: [{"title": ..., "score": ...}].
    # Sahifa yangilanganda ham manba chiplari ko'rinib turishi uchun saqlanadi.
    sources: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)


class QuestionLog(Base, UUIDIDMixin, TimestampMixin):
    """Botga berilgan har bir savol — admin tahlili uchun.

    "Eng ko'p so'ralgan" va "javob topilmagan" savollar shu jadvaldan
    hisoblanadi; ular bilim bazasiga nima qo'shish kerakligini ko'rsatadi.
    Chat tarixidan alohida: suhbat o'chirilsa ham statistika qoladi.
    """

    __tablename__ = "question_logs"

    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    question: Mapped[str] = mapped_column(Text)
    # Guruhlash kaliti: kichik harf, lotin, tinish belgisiz, bo'shliqlar bitta
    normalized: Mapped[str] = mapped_column(String(300), index=True)
    # Router aniqlagan niyat (product, employee, concept, ...) — bo'lmasa NULL
    intent: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # "answered" | "no_info" (bazada topilmadi) | "blocked" (prompt-injection)
    # | "flagged" (xavfli so'rov / so'kinish, intent'da sababi)
    # | "web" (bazada yo'q, ruxsat etilgan saytdan javob berildi) | "error"
    outcome: Mapped[str] = mapped_column(String(20), index=True)
    top_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sources_count: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    # Savol kelgandan javob tugaguncha (ms)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    # outcome="web" bo'lsa — javob olingan sahifalar (admin bazaga qo'shishi uchun)
    source_urls: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.repositories import BaseRepository, SoftDeleteRepository
from src.core.utils.datetime_utils import get_utc_now
from src.chat.models import ChatMessage, ChatSession
from src.user.models import User


class ChatSessionRepository(SoftDeleteRepository[ChatSession]):
    model = ChatSession

    async def list_for_user(
        self, session: AsyncSession, user_id: UUID
    ) -> list[ChatSession]:
        """Foydalanuvchining suhbatlari — pin qilinganlari tepada, ular ichida ham,
        oddiylar ichida ham eng so'nggi yangilangani birinchi."""
        query = (
            select(self.model)
            .where(self.model.user_id == user_id)
            .where(self.model.is_deleted.is_(False))
            .order_by(self.model.is_pinned.desc(), self.model.updated_at.desc())
        )
        result = await session.execute(query)
        return list(result.scalars().all())


class ChatMessageRepository(BaseRepository[ChatMessage]):
    model = ChatMessage

    async def list_by_session(
        self, session: AsyncSession, session_id: UUID
    ) -> list[ChatMessage]:
        """Suhbat xabarlari — vaqt bo'yicha eskidan yangiga."""
        query = (
            select(self.model)
            .where(self.model.session_id == session_id)
            .order_by(self.model.created_at.asc())
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    async def count_per_day(
        self, session: AsyncSession, days: int = 7
    ) -> dict[date, int]:
        """So'nggi `days` kun ichida har bir kundagi xabarlar soni."""
        since = get_utc_now() - timedelta(days=days)
        day_col = func.date(self.model.created_at)
        query = (
            select(day_col, func.count())
            .where(self.model.created_at >= since)
            .group_by(day_col)
        )
        result = await session.execute(query)
        return {row[0]: int(row[1]) for row in result.all()}

    async def count_requests_by_department(
        self, session: AsyncSession
    ) -> list[tuple[str | None, int]]:
        """Bo'lim bo'yicha so'rovlar (user xabarlari) soni."""
        query = (
            select(User.department, func.count())
            .select_from(ChatMessage)
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .join(User, ChatSession.user_id == User.id)
            .where(ChatMessage.role == "user")
            .group_by(User.department)
        )
        result = await session.execute(query)
        return [(row[0], int(row[1])) for row in result.all()]

    async def top_users_by_requests(
        self, session: AsyncSession, days: int = 30, limit: int = 5
    ) -> list[tuple[str, str, str | None, int]]:
        """So'nggi `days` kunda eng ko'p savol bergan (user xabarlari) xodimlar:
        (ism, login, bo'lim, so'rovlar soni) — ko'pidan kamiga."""
        since = get_utc_now() - timedelta(days=days)
        cnt = func.count(ChatMessage.id)
        query = (
            select(User.first_name, User.last_name, User.username, User.department, cnt)
            .select_from(ChatMessage)
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .join(User, ChatSession.user_id == User.id)
            .where(ChatMessage.role == "user")
            .where(ChatMessage.created_at >= since)
            .where(User.is_deleted.is_(False))
            .group_by(User.id, User.first_name, User.last_name, User.username, User.department)
            .order_by(cnt.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return [
            (f"{r[0] or ''} {r[1] or ''}".strip(), r[2], r[3], int(r[4]))
            for r in result.all()
        ]

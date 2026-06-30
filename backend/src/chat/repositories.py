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
        """Foydalanuvchining suhbatlari — eng so'nggi yangilangani birinchi."""
        query = (
            select(self.model)
            .where(self.model.user_id == user_id)
            .where(self.model.is_deleted.is_(False))
            .order_by(self.model.updated_at.desc())
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

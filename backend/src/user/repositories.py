from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from loggers import get_logger
from src.core.database.repositories import BaseRepository, SoftDeleteRepository
from src.user.models import LoginEvent, User

logger = get_logger(__name__)


class UserRepository(SoftDeleteRepository[User]):

    model = User

    async def search_list(
        self,
        session: AsyncSession,
        search: str | None = None,
        department: str | None = None,
    ) -> list[User]:
        """Ism/familiya/login bo'yicha qidiruv + bo'lim filtri bilan ro'yxat."""
        query = select(self.model).where(self.model.is_deleted.is_(False))
        query = self._apply_search_filter(
            query, search=search, fields=["first_name", "last_name", "username"]
        )
        if department:
            query = query.where(self.model.department == department)
        query = self._apply_default_ordering(query)

        result = await session.execute(query)
        return list(result.unique().scalars().all())

    async def count_by_department(
        self, session: AsyncSession
    ) -> list[tuple[str | None, int]]:
        """Har bir bo'limdagi (o'chirilmagan) foydalanuvchilar soni."""
        query = (
            select(self.model.department, func.count())
            .where(self.model.is_deleted.is_(False))
            .group_by(self.model.department)
        )
        result = await session.execute(query)
        return [(row[0], int(row[1])) for row in result.all()]


class LoginEventRepository(BaseRepository[LoginEvent]):

    model = LoginEvent

    async def recent_with_users(
        self, session: AsyncSession, limit: int = 8
    ) -> list[tuple[str, datetime]]:
        """So'nggi loginlar — foydalanuvchi ismi + vaqti bilan."""
        query = (
            select(LoginEvent.created_at, User.first_name, User.last_name)
            .join(User, LoginEvent.user_id == User.id)
            .order_by(LoginEvent.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return [(f"{r[1]} {r[2]}".strip(), r[0]) for r in result.all()]

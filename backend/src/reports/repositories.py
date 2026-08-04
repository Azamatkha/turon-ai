from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.repositories import BaseRepository
from src.reports.models import UserReport
from src.user.models import User


class UserReportRepository(BaseRepository[UserReport]):
    model = UserReport

    async def list_with_users(
        self,
        session: AsyncSession,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[tuple[UserReport, User]], int]:
        """Murojaatlar + muallifi, yangisidan eskisiga. (ro'yxat, jami) qaytaradi."""
        count_query = select(func.count()).select_from(self.model)
        if status is not None:
            count_query = count_query.where(self.model.status == status)
        total = int((await session.execute(count_query)).scalar_one())

        query = select(self.model, User).join(User, self.model.user_id == User.id)
        if status is not None:
            query = query.where(self.model.status == status)
        query = (
            query.order_by(self.model.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await session.execute(query)
        return [(row[0], row[1]) for row in result.all()], total

    async def get_with_user(
        self, session: AsyncSession, report_id: UUID
    ) -> tuple[UserReport, User] | None:
        """Bitta murojaat + muallifi."""
        query = (
            select(self.model, User)
            .join(User, self.model.user_id == User.id)
            .where(self.model.id == report_id)
            .limit(1)
        )
        result = await session.execute(query)
        row = result.first()
        return (row[0], row[1]) if row else None

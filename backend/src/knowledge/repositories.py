from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.repositories import BaseRepository
from src.knowledge.models import KbCategory


class KbCategoryRepository(BaseRepository[KbCategory]):
    model = KbCategory

    async def list_ordered(self, session: AsyncSession) -> list[KbCategory]:
        """Barcha turkumlar — admin belgilagan tartibda, keyin nomi bo'yicha."""
        query = select(self.model).order_by(self.model.sort_order, self.model.name)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def max_sort_order(self, session: AsyncSession) -> int:
        result = await session.execute(select(func.max(self.model.sort_order)))
        return int(result.scalar() or 0)

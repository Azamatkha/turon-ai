from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.repositories import BaseRepository
from src.guides.models import EdoGuide


class EdoGuideRepository(BaseRepository[EdoGuide]):
    model = EdoGuide

    async def list_by_title(self, session: AsyncSession) -> list[EdoGuide]:
        """Barcha yo'riqnomalar — sarlavha bo'yicha alifbo tartibida."""
        query = select(self.model).order_by(self.model.title)
        result = await session.execute(query)
        return list(result.scalars().all())

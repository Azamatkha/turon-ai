from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.models import AuditLog
from src.core.database.repositories import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    async def list_page(
        self,
        session: AsyncSession,
        target_type: str | None = None,
        search: str | None = None,
        page: int = 1,
        size: int = 50,
    ) -> tuple[list[AuditLog], int]:
        """Yozuvlar yangisidan eskisiga. `search` — bajaruvchi logini yoki
        obyekt nomi bo'yicha. (ro'yxat, jami) qaytaradi."""
        conds = []
        if target_type:
            conds.append(self.model.target_type == target_type)
        if search:
            like = f"%{search.strip().lower()}%"
            conds.append(
                func.lower(self.model.actor_username).like(like)
                | func.lower(func.coalesce(self.model.target_label, "")).like(like)
            )
        total = int(
            (
                await session.execute(
                    select(func.count()).select_from(self.model).where(*conds)
                )
            ).scalar_one()
        )
        query = (
            select(self.model)
            .where(*conds)
            .order_by(self.model.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await session.execute(query)
        return list(result.scalars().all()), total

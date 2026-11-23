from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.repositories import BaseRepository
from src.evaluation.enums import ACTIVE_STATUSES
from src.evaluation.models import EvalCaseRow, EvalResultRow, EvalRun


class EvalCaseRepository(BaseRepository[EvalCaseRow]):
    model = EvalCaseRow

    async def list_all(self, session: AsyncSession) -> list[EvalCaseRow]:
        query = select(self.model).order_by(self.model.doc_title, self.model.style)
        return list((await session.execute(query)).scalars().all())

    async def replace_all(self, session: AsyncSession, rows: list[dict[str, object]]) -> None:
        """Savollar to'plamini to'liq almashtiradi (eski o'lchov natijalari
        o'z nusxasini saqlaydi — case_id NULL bo'ladi)."""
        await session.execute(delete(self.model))
        session.add_all([self.model(**r) for r in rows])

    async def count_by_style(self, session: AsyncSession) -> dict[str, int]:
        query = select(self.model.style, func.count()).group_by(self.model.style)
        return {str(s): int(n) for s, n in (await session.execute(query)).all()}


class EvalRunRepository(BaseRepository[EvalRun]):
    model = EvalRun

    async def list_recent(self, session: AsyncSession, limit: int = 30) -> list[EvalRun]:
        query = select(self.model).order_by(self.model.created_at.desc()).limit(limit)
        return list((await session.execute(query)).scalars().all())

    async def active(self, session: AsyncSession) -> list[EvalRun]:
        query = select(self.model).where(self.model.status.in_(ACTIVE_STATUSES))
        return list((await session.execute(query)).scalars().all())

    async def previous_done(self, session: AsyncSession, before: EvalRun) -> EvalRun | None:
        """Shu o'lchovdan oldingi tugagan o'lchov — "avval/endi" uchun."""
        query = (
            select(self.model)
            .where(self.model.status == "done", self.model.created_at < before.created_at)
            .order_by(self.model.created_at.desc())
            .limit(1)
        )
        return (await session.execute(query)).scalars().first()


class EvalResultRepository(BaseRepository[EvalResultRow]):
    model = EvalResultRow

    async def list_for_run(
        self, session: AsyncSession, run_id: UUID, failed_only: bool = False
    ) -> list[EvalResultRow]:
        query = select(self.model).where(self.model.run_id == run_id)
        if failed_only:
            query = query.where(self.model.passed.is_(False))
        query = query.order_by(self.model.doc_title, self.model.style)
        return list((await session.execute(query)).scalars().all())

    async def done_case_ids(self, session: AsyncSession, run_id: UUID) -> set[UUID]:
        query = select(self.model.case_id).where(
            self.model.run_id == run_id, self.model.case_id.is_not(None)
        )
        return {cid for cid in (await session.execute(query)).scalars().all() if cid}

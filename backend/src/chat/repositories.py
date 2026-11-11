from datetime import date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from src.chat.models import ChatMessage, ChatSession, QuestionLog
from src.core.database.repositories import BaseRepository, SoftDeleteRepository
from src.core.utils.datetime_utils import get_utc_now
from src.user.models import User


class ChatSessionRepository(SoftDeleteRepository[ChatSession]):
    model = ChatSession

    async def search_messages(
        self,
        session: AsyncSession,
        user_id: UUID,
        patterns: list[str],
        limit: int = 30,
    ) -> list[tuple[ChatMessage, str]]:
        """Foydalanuvchining O'Z (o'chirilmagan) suhbatlaridagi xabarlar —
        matni yoki suhbat sarlavhasi `patterns`dan biriga mos keladigan
        (ILIKE, katta-kichik harfsiz). Yangisidan eskisiga.

        `patterns` — tayyor LIKE naqshlari (`%...%`, maxsus belgilar
        ekranlangan). (xabar, suhbat sarlavhasi) qaytaradi."""
        conds = []
        for pat in patterns:
            conds.append(ChatMessage.content.ilike(pat, escape="\\"))
            conds.append(self.model.title.ilike(pat, escape="\\"))
        query = (
            select(ChatMessage, self.model.title)
            .join(self.model, self.model.id == ChatMessage.session_id)
            .where(self.model.user_id == user_id)
            .where(self.model.is_deleted.is_(False))
            .where(or_(*conds))
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return [(row[0], row[1] or "") for row in result.all()]

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
        self, session: AsyncSession, days: int = 7, role: str | None = None
    ) -> dict[date, int]:
        """So'nggi `days` kun ichida har bir kundagi xabarlar soni.

        `role` berilsa — faqat shu roldagi xabarlar (masalan "user" = so'rovlar).
        """
        since = get_utc_now() - timedelta(days=days)
        day_col = func.date(self.model.created_at)
        query = select(day_col, func.count()).where(self.model.created_at >= since)
        if role is not None:
            query = query.where(self.model.role == role)
        query = query.group_by(day_col)
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

    async def list_disliked(
        self,
        session: AsyncSession,
        only_open: bool = True,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[tuple[ChatMessage, str | None, str, str, str]], int]:
        """Dislike olgan assistant javoblari (yangisidan eskisiga).

        Har qator: (xabar, shu javobdan oldingi user savoli, suhbat sarlavhasi,
        user ismi, login). (ro'yxat, jami) qaytaradi.
        """
        conds = [self.model.vote == "down", self.model.role == "assistant"]
        if only_open:
            conds.append(self.model.vote_reviewed.is_(False))

        # Savol — shu suhbatda javobdan oldingi eng so'nggi user xabari
        q = aliased(ChatMessage)
        question = (
            select(q.content)
            .where(q.session_id == self.model.session_id)
            .where(q.role == "user")
            .where(q.created_at <= self.model.created_at)
            .order_by(q.created_at.desc())
            .limit(1)
            .correlate(self.model)
            .scalar_subquery()
        )
        base = (
            select(self.model)
            .join(ChatSession, ChatSession.id == self.model.session_id)
            .join(User, User.id == ChatSession.user_id)
            .where(*conds)
        )
        total = int(
            (
                await session.execute(
                    select(func.count()).select_from(base.subquery())
                )
            ).scalar_one()
        )
        query = (
            base.add_columns(
                question,
                ChatSession.title,
                User.first_name,
                User.last_name,
                User.username,
            )
            .order_by(self.model.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await session.execute(query)
        return [
            (
                r[0],
                r[1],
                r[2] or "",
                f"{r[3] or ''} {r[4] or ''}".strip(),
                r[5],
            )
            for r in result.all()
        ], total


class QuestionLogRepository(BaseRepository[QuestionLog]):
    model = QuestionLog

    async def top_questions(
        self,
        session: AsyncSession,
        days: int = 30,
        limit: int = 20,
        outcome: str | None = None,
    ) -> list[tuple[str, int, int, datetime]]:
        """Bir xil (normallashtirilgan) savollar guruhi, ko'pidan oziga.

        `outcome` berilsa — faqat shu natijali savollar (masalan "no_info").
        Har qator: (namuna savol, soni, nechta xodim so'ragan, oxirgi marta).
        """
        since = get_utc_now() - timedelta(days=days)
        cnt = func.count()
        query = (
            select(
                func.min(self.model.question),
                cnt,
                func.count(func.distinct(self.model.user_id)),
                func.max(self.model.created_at),
            )
            .where(self.model.created_at >= since)
            .where(self.model.normalized != "")
        )
        if outcome is not None:
            query = query.where(self.model.outcome == outcome)
        query = (
            query.group_by(self.model.normalized)
            .order_by(cnt.desc(), func.max(self.model.created_at).desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return [(r[0], int(r[1]), int(r[2]), r[3]) for r in result.all()]

    async def summary(
        self, session: AsyncSession, days: int = 30
    ) -> tuple[int, int, int, float, int]:
        """(jami, javobsiz, xato, o'rtacha javob vaqti ms, jami token)."""
        since = get_utc_now() - timedelta(days=days)
        query = select(
            func.count(),
            func.count().filter(self.model.outcome == "no_info"),
            func.count().filter(self.model.outcome == "error"),
            func.coalesce(func.avg(self.model.duration_ms), 0),
            func.coalesce(func.sum(self.model.completion_tokens), 0),
        ).where(self.model.created_at >= since)
        r = (await session.execute(query)).one()
        return int(r[0]), int(r[1]), int(r[2]), float(r[3]), int(r[4])

    async def hourly(
        self, session: AsyncSession, hours: int = 24
    ) -> list[tuple[datetime, int, int, int, float]]:
        """Soatbay: (soat boshi, savollar, xatolar, javobsiz, o'rtacha ms)."""
        since = get_utc_now() - timedelta(hours=hours)
        hour = func.date_trunc("hour", self.model.created_at)
        query = (
            select(
                hour,
                func.count(),
                func.count().filter(self.model.outcome == "error"),
                func.count().filter(self.model.outcome == "no_info"),
                func.coalesce(func.avg(self.model.duration_ms), 0),
            )
            .where(self.model.created_at >= since)
            .group_by(hour)
            .order_by(hour)
        )
        result = await session.execute(query)
        return [(r[0], int(r[1]), int(r[2]), int(r[3]), float(r[4])) for r in result.all()]

    async def latency_percentiles(
        self, session: AsyncSession, hours: int = 24
    ) -> tuple[int, int, int]:
        """Javob vaqti (ms): p50, p95, max — xato bilan tugaganlarsiz."""
        since = get_utc_now() - timedelta(hours=hours)
        query = select(
            func.percentile_cont(0.5).within_group(self.model.duration_ms),
            func.percentile_cont(0.95).within_group(self.model.duration_ms),
            func.max(self.model.duration_ms),
        ).where(self.model.created_at >= since, self.model.outcome != "error")
        r = (await session.execute(query)).one()
        return int(r[0] or 0), int(r[1] or 0), int(r[2] or 0)

    async def list_flagged(
        self, session: AsyncSession, page: int = 1, size: int = 50
    ) -> tuple[list[tuple[QuestionLog, str | None, str]], int]:
        """Xavfli deb belgilangan so'rovlar (outcome="flagged"), yangisidan.
        Har qator: (yozuv, login, F.I.Sh.). User o'chirilgan bo'lsa — None."""
        return await self.list_by_outcome(session, "flagged", page=page, size=size)

    async def list_by_outcome(
        self, session: AsyncSession, outcome: str, page: int = 1, size: int = 50
    ) -> tuple[list[tuple[QuestionLog, str | None, str]], int]:
        """Berilgan natijali yozuvlar (flagged, web, ...), yangisidan."""
        cond = self.model.outcome == outcome
        total = int(
            (await session.execute(select(func.count()).select_from(self.model).where(cond))).scalar_one()
        )
        query = (
            select(self.model, User.username, User.first_name, User.last_name)
            .outerjoin(User, User.id == self.model.user_id)
            .where(cond)
            .order_by(self.model.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        rows = (await session.execute(query)).all()
        return [
            (r[0], r[1], f"{r[2] or ''} {r[3] or ''}".strip()) for r in rows
        ], total

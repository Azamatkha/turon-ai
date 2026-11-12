from typing import Any, Literal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.repositories import BaseRepository
from src.core.utils.datetime_utils import get_utc_now
from src.telegram_bot.models import TelegramBotMessage, TelegramBotUser

PENDING_STATUS = "new"
INCOMING = "in"
REG_DONE = "done"

# Admin paneldagi filtr va saralash qiymatlari
TgUserFilter = Literal["pending", "registered", "unregistered", "banned"]
TgUserSort = Literal["joined", "last_message"]


class TelegramBotUserRepository(BaseRepository[TelegramBotUser]):
    model = TelegramBotUser

    async def upsert_many(
        self, session: AsyncSession, rows: list[dict[str, Any]]
    ) -> dict[int, UUID]:
        """telegram_id bo'yicha qo'shadi yoki yangilaydi. {telegram_id: id} qaytaradi."""
        if not rows:
            return {}
        now = get_utc_now()
        stmt = insert(self.model).values(
            [{**row, "created_at": now, "updated_at": now} for row in rows]
        )
        update_cols = {
            col: stmt.excluded[col] for col in rows[0] if col != "telegram_id"
        }
        update_cols["updated_at"] = stmt.excluded.updated_at
        upsert = stmt.on_conflict_do_update(
            index_elements=[self.model.telegram_id], set_=update_cols
        ).returning(self.model.telegram_id, self.model.id)
        result = await session.execute(upsert)
        return {telegram_id: user_id for telegram_id, user_id in result.all()}

    async def ids_by_telegram_ids(
        self, session: AsyncSession, telegram_ids: set[int]
    ) -> dict[int, UUID]:
        if not telegram_ids:
            return {}
        query = select(self.model.telegram_id, self.model.id).where(
            self.model.telegram_id.in_(telegram_ids)
        )
        result = await session.execute(query)
        return {telegram_id: user_id for telegram_id, user_id in result.all()}

    async def list_with_counts(
        self,
        session: AsyncSession,
        search: str | None = None,
        page: int = 1,
        size: int = 20,
        status: TgUserFilter | None = None,
        sort: TgUserSort = "joined",
    ) -> tuple[list[tuple[TelegramBotUser, int, int]], int]:
        """Userlar + xabarlar soni + javob kutayotganlar soni. (ro'yxat, jami).

        Standart saralash — botga kirgan vaqti (yangisi tepada)."""
        msg = TelegramBotMessage
        conditions = []
        if search:
            term = search.strip().lstrip("@")
            pattern = f"%{term}%"
            fields = [
                self.model.full_name.ilike(pattern),
                self.model.username.ilike(pattern),
                self.model.phone.ilike(pattern),
            ]
            # Raqam yozilsa — Telegram ID bo'yicha ham aniq qidiramiz
            if term.isdigit():
                fields.append(self.model.telegram_id == int(term))
            conditions.append(or_(*fields))
        if status == "pending":
            conditions.append(
                select(msg.id)
                .where(
                    msg.user_id == self.model.id,
                    msg.direction == INCOMING,
                    msg.status == PENDING_STATUS,
                )
                .exists()
            )
        elif status == "registered":
            conditions.append(self.model.reg_step == REG_DONE)
        elif status == "unregistered":
            conditions.append(self.model.reg_step != REG_DONE)
        elif status == "banned":
            conditions.append(self.model.is_banned.is_(True))

        count_query = select(func.count()).select_from(self.model).where(*conditions)
        total = int((await session.execute(count_query)).scalar_one())

        messages_count = (
            select(func.count())
            .where(msg.user_id == self.model.id)
            .correlate(self.model)
            .scalar_subquery()
        )
        pending_count = (
            select(func.count())
            .where(
                msg.user_id == self.model.id,
                msg.direction == INCOMING,
                msg.status == PENDING_STATUS,
            )
            .correlate(self.model)
            .scalar_subquery()
        )
        order = (
            [
                self.model.last_message_at.desc().nulls_last(),
                self.model.first_seen_at.desc(),
            ]
            if sort == "last_message"
            else [self.model.first_seen_at.desc(), self.model.telegram_id.desc()]
        )
        query = (
            select(self.model, messages_count, pending_count)
            .where(*conditions)
            .order_by(*order)
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await session.execute(query)
        return [(row[0], int(row[1]), int(row[2])) for row in result.all()], total

    async def get_with_counts(
        self, session: AsyncSession, user_id: UUID
    ) -> tuple[TelegramBotUser, int, int] | None:
        user = await self.get_single(session, id=user_id)
        if not user:
            return None
        msg = TelegramBotMessage
        query = select(
            func.count(),
            func.count().filter(
                msg.direction == INCOMING, msg.status == PENDING_STATUS
            ),
        ).where(msg.user_id == user_id)
        total, pending = (await session.execute(query)).one()
        return user, int(total), int(pending)


class TelegramBotMessageRepository(BaseRepository[TelegramBotMessage]):
    model = TelegramBotMessage

    async def upsert_many(
        self, session: AsyncSession, rows: list[dict[str, Any]]
    ) -> int:
        """bot_message_id bo'yicha qo'shadi yoki yangilaydi."""
        if not rows:
            return 0
        now = get_utc_now()
        stmt = insert(self.model).values(
            [{**row, "created_at": now, "updated_at": now} for row in rows]
        )
        update_cols = {
            col: stmt.excluded[col] for col in rows[0] if col != "bot_message_id"
        }
        update_cols["updated_at"] = stmt.excluded.updated_at
        stmt = stmt.on_conflict_do_update(
            index_elements=[self.model.bot_message_id], set_=update_cols
        )
        await session.execute(stmt)
        return len(rows)

    async def list_for_user(
        self, session: AsyncSession, user_id: UUID, page: int = 1, size: int = 50
    ) -> tuple[list[TelegramBotMessage], int]:
        """Userning yozishmalari, yangisidan eskisiga. (ro'yxat, jami)."""
        count_query = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.user_id == user_id)
        )
        total = int((await session.execute(count_query)).scalar_one())
        query = (
            select(self.model)
            .where(self.model.user_id == user_id)
            .order_by(self.model.sent_at.desc(), self.model.bot_message_id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await session.execute(query)
        return list(result.scalars().all()), total

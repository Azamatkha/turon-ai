from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.repositories import BaseRepository
from src.core.utils.datetime_utils import get_utc_now
from src.notifications.models import Notification
from src.user.enums import UserRole
from src.user.models import User


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    async def list_for_user(
        self,
        session: AsyncSession,
        user_id: UUID,
        limit: int = 30,
        offset: int = 0,
        only_unread: bool = False,
    ) -> list[Notification]:
        """Foydalanuvchi bildirishnomalari — yangisidan eskisiga."""
        query = select(self.model).where(self.model.user_id == user_id)
        if only_unread:
            query = query.where(self.model.is_read.is_(False))
        query = (
            query.order_by(self.model.created_at.desc()).offset(offset).limit(limit)
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    async def mark_all_read(self, session: AsyncSession, user_id: UUID) -> int:
        """Foydalanuvchining barcha o'qilmaganlarini o'qilgan deb belgilaydi.

        Commit qilmaydi — chaqiruvchi UoW commit qiladi.
        """
        query = (
            update(self.model)
            .where(self.model.user_id == user_id, self.model.is_read.is_(False))
            .values(is_read=True, read_at=get_utc_now())
        )
        result = await session.execute(query)
        return int(result.rowcount) if hasattr(result, "rowcount") else 0

    async def delete_older_than(
        self,
        session: AsyncSession,
        read_before: datetime,
        any_before: datetime,
    ) -> int:
        """Eskirgan bildirishnomalarni o'chiradi.

        O'qilganlari `read_before` dan oldin bo'lsa, o'qilmaganlari esa ancha
        eski (`any_before`) bo'lsa tozalanadi. Jadval har broadcast'da har bir
        foydalanuvchi uchun bittadan qator oladi — cheklovsiz o'sib ketmasin.

        Commit qilmaydi — chaqiruvchi UoW commit qiladi.
        """
        query = delete(self.model).where(
            or_(
                (self.model.is_read.is_(True)) & (self.model.created_at < read_before),
                self.model.created_at < any_before,
            )
        )
        result = await session.execute(query)
        return int(result.rowcount) if hasattr(result, "rowcount") else 0

    async def fan_out(
        self,
        session: AsyncSession,
        notification_type: str,
        params: dict[str, str] | None = None,
        entity_id: UUID | None = None,
        role: UserRole | None = None,
    ) -> int:
        """Bitta xabarni bir nechta foydalanuvchiga tarqatadi.

        `role` berilsa faqat o'sha roldagilar, aks holda barcha aktiv
        foydalanuvchilar oladi. Har bir qabul qiluvchiga alohida qator
        yoziladi — shunda o'qilmaganlar soni oddiy partial-indeks bo'yicha
        COUNT bo'lib qoladi (poll so'rovi eng issiq so'rov).

        Commit qilmaydi — chaqiruvchi UoW commit qiladi.
        Qaytaradi: nechta foydalanuvchiga yozilgani.
        """
        query = select(User.id).where(
            User.is_deleted.is_(False), User.is_active.is_(True)
        )
        if role is not None:
            query = query.where(User.role == role)
        result = await session.execute(query)
        user_ids = list(result.scalars().all())
        if not user_ids:
            return 0

        # id/created_at/updated_at ni ataylab o'zimiz to'ldiramiz: executemany
        # rejimida ustun default'lariga tayanmaslik ancha ishonchli.
        now = get_utc_now()
        rows: list[dict[str, Any]] = [
            {
                "id": uuid4(),
                "created_at": now,
                "updated_at": now,
                "user_id": user_id,
                "type": notification_type,
                "params": params or {},
                "entity_id": entity_id,
            }
            for user_id in user_ids
        ]
        await session.execute(insert(self.model), rows)
        return len(user_ids)

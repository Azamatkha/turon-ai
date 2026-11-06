from datetime import timedelta
from uuid import UUID

from fastapi import Depends

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import InstanceNotFoundException
from src.core.schemas import SuccessResponse
from src.core.utils.datetime_utils import get_utc_now
from src.notifications.enums import NotificationType
from src.notifications.events import publish_new
from src.notifications.schemas import (
    NotificationListView,
    NotificationView,
    UnreadCountView,
)
from src.user.enums import UserRole

logger = get_logger(__name__)

NOTIFICATION_NOT_FOUND = "Bildirishnoma topilmadi"

# BIRLASHTIRISH OYNASI — qaysi tur uchun necha vaqt ichida kelgan xabarlar
# BITTA bildirishnomaga qo'shiladi.
#
# NEGA: bilim bazasiga ma'lumot qo'shish bitta emas, ko'p amal bo'ladi —
# admin ScrapeModal'ga bir necha o'nlab havolani birdan tashlaydi va frontend
# ularni ketma-ket, HAR BIRI uchun alohida so'rov qilib yuboradi. Har so'rov
# esa broadcast qilardi: 100 havola -> har bir xodimga 100 ta bildirishnoma.
# So'rovlarni serverda birlashtirib bo'lmaydi (ular alohida keladi), shuning
# uchun birlashtirish bildirishnoma yozish bosqichida qilinadi.
#
# Ro'yxatda YO'Q turlar birlashtirilmaydi:
#   RATES_UPDATED — kuniga bir marta, birlashtiradigan narsa yo'q;
#   REPORT_NEW    — har murojaat alohida voqea, qo'shib yuborish noto'g'ri.
COALESCE_WINDOWS: dict[str, timedelta] = {
    NotificationType.KNOWLEDGE_UPDATED.value: timedelta(minutes=10),
}


class ListNotificationsUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self,
        user_id: UUID,
        limit: int = 30,
        offset: int = 0,
        only_unread: bool = False,
    ) -> NotificationListView:
        async with self.uow as uow:
            items = await uow.notifications.list_for_user(
                uow.session,
                user_id=user_id,
                limit=limit,
                offset=offset,
                only_unread=only_unread,
            )
            unread_count = await uow.notifications.count(
                uow.session, user_id=user_id, is_read=False
            )
            total = await uow.notifications.count(uow.session, user_id=user_id)
            return NotificationListView(
                items=[NotificationView.model_validate(i) for i in items],
                unread_count=unread_count,
                total=total,
            )


class UnreadCountUseCase:
    """Frontend buni interval bilan so'raydi — imkon qadar yengil bo'lishi kerak."""

    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, user_id: UUID) -> UnreadCountView:
        async with self.uow as uow:
            count = await uow.notifications.count(
                uow.session, user_id=user_id, is_read=False
            )
            return UnreadCountView(count=count)


class MarkReadUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, user_id: UUID, notification_id: UUID) -> SuccessResponse:
        async with self.uow as uow:
            # user_id bo'yicha ham filtrlaymiz — birovnikini o'qilgan deb
            # belgilab bo'lmaydi, topilmagandek 404 qaytadi.
            notification = await uow.notifications.get_single(
                uow.session, id=notification_id, user_id=user_id
            )
            if not notification:
                raise InstanceNotFoundException(NOTIFICATION_NOT_FOUND)
            if not notification.is_read:
                notification.is_read = True
                notification.read_at = get_utc_now()
            await uow.commit()
            return SuccessResponse(success=True)


class MarkAllReadUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, user_id: UUID) -> SuccessResponse:
        async with self.uow as uow:
            await uow.notifications.mark_all_read(uow.session, user_id=user_id)
            await uow.commit()
            return SuccessResponse(success=True)


class BroadcastNotificationUseCase:
    """Tizim xabarini foydalanuvchilarga tarqatadi.

    Bildirishnoma yuborishdagi xato asosiy amalni (masalan hujjat yuklashni)
    yiqitmasligi kerak — shu sababli xatolar ushlanadi va faqat logga yoziladi.
    """

    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self,
        notification_type: str,
        params: dict[str, str] | None = None,
        entity_id: UUID | None = None,
        role: UserRole | None = None,
    ) -> int:
        window = COALESCE_WINDOWS.get(notification_type)
        coalesce_after = get_utc_now() - window if window else None
        try:
            async with self.uow as uow:
                recipients = await uow.notifications.fan_out(
                    uow.session,
                    notification_type=notification_type,
                    params=params,
                    entity_id=entity_id,
                    role=role,
                    coalesce_after=coalesce_after,
                )
                await uow.commit()
            # Signal commit'dan KEYIN — klient so'raganda qator ko'rinadigan bo'lsin
            await publish_new(recipients)
            return len(recipients)
        except Exception:
            logger.exception(
                "Bildirishnomani tarqatib bo'lmadi: type=%s", notification_type
            )
            return 0


# ---- DI factory'lar ----
def get_list_notifications_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> ListNotificationsUseCase:
    return ListNotificationsUseCase(uow=uow)


def get_unread_count_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> UnreadCountUseCase:
    return UnreadCountUseCase(uow=uow)


def get_mark_read_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> MarkReadUseCase:
    return MarkReadUseCase(uow=uow)


def get_mark_all_read_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> MarkAllReadUseCase:
    return MarkAllReadUseCase(uow=uow)


def get_broadcast_notification_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> BroadcastNotificationUseCase:
    return BroadcastNotificationUseCase(uow=uow)

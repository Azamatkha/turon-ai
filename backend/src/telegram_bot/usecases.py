from uuid import UUID

from fastapi import Depends

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import InstanceNotFoundException
from src.telegram_bot.models import TelegramBotUser
from src.telegram_bot.repositories import TgUserFilter, TgUserSort
from src.telegram_bot.schemas import (
    BotSyncRequest,
    BotSyncResult,
    TgMessagePage,
    TgMessageView,
    TgUserPage,
    TgUserView,
)

logger = get_logger(__name__)

TG_USER_NOT_FOUND = "Telegram user topilmadi"


def _to_user_view(
    user: TelegramBotUser, messages_count: int = 0, pending_count: int = 0
) -> TgUserView:
    view = TgUserView.model_validate(user)
    view.messages_count = messages_count
    view.pending_count = pending_count
    return view


class SyncBotDataUseCase:
    """Botdan kelgan userlar va xabarlarni upsert qiladi (bitta tranzaksiyada)."""

    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, data: BotSyncRequest) -> BotSyncResult:
        # Bitta so'rovda bir xil kalit ikki marta kelsa, oxirgisi qoladi —
        # aks holda Postgres ON CONFLICT bitta qatorni ikki marta yangilay olmaydi
        users = {u.telegram_id: u.model_dump() for u in data.users}
        messages = {m.bot_message_id: m.model_dump() for m in data.messages}

        async with self.uow as uow:
            user_ids = await uow.telegram_bot_users.upsert_many(
                uow.session, list(users.values())
            )
            missing = {m["telegram_id"] for m in messages.values()} - user_ids.keys()
            if missing:
                user_ids |= await uow.telegram_bot_users.ids_by_telegram_ids(
                    uow.session, missing
                )

            rows, skipped = [], 0
            for message in messages.values():
                user_id = user_ids.get(message.pop("telegram_id"))
                if user_id is None:
                    skipped += 1
                    continue
                rows.append({**message, "user_id": user_id})
            saved = await uow.telegram_bot_messages.upsert_many(uow.session, rows)
            await uow.commit()

        if skipped:
            logger.warning(
                "Telegram bot sync: %s ta xabarning useri topilmadi", skipped
            )
        return BotSyncResult(users=len(users), messages=saved, skipped_messages=skipped)


class ListTgUsersUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self,
        search: str | None = None,
        page: int = 1,
        size: int = 20,
        status: TgUserFilter | None = None,
        sort: TgUserSort = "joined",
    ) -> TgUserPage:
        async with self.uow as uow:
            rows, total = await uow.telegram_bot_users.list_with_counts(
                uow.session,
                search=search,
                page=page,
                size=size,
                status=status,
                sort=sort,
            )
            return TgUserPage(
                items=[_to_user_view(u, count, pending) for u, count, pending in rows],
                total=total,
            )


class ListTgMessagesUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self, user_id: UUID, page: int = 1, size: int = 50
    ) -> TgMessagePage:
        async with self.uow as uow:
            row = await uow.telegram_bot_users.get_with_counts(uow.session, user_id)
            if not row:
                raise InstanceNotFoundException(TG_USER_NOT_FOUND)
            messages, total = await uow.telegram_bot_messages.list_for_user(
                uow.session, user_id, page=page, size=size
            )
            return TgMessagePage(
                user=_to_user_view(*row),
                items=[TgMessageView.model_validate(m) for m in messages],
                total=total,
            )


# ---- DI factory'lar ----
def get_sync_bot_data_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> SyncBotDataUseCase:
    return SyncBotDataUseCase(uow=uow)


def get_list_tg_users_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> ListTgUsersUseCase:
    return ListTgUsersUseCase(uow=uow)


def get_list_tg_messages_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> ListTgMessagesUseCase:
    return ListTgMessagesUseCase(uow=uow)

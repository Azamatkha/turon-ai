from uuid import UUID

from fastapi import Depends

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import InstanceNotFoundException
from src.core.schemas import SuccessResponse
from src.core.utils.datetime_utils import get_utc_now
from src.chat.schemas import (
    AddMessageModel,
    MessageView,
    SessionDetailView,
    SessionView,
)

logger = get_logger(__name__)

SESSION_NOT_FOUND = "Suhbat topilmadi"


class ListSessionsUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, user_id: UUID) -> list[SessionView]:
        async with self.uow as uow:
            sessions = await uow.chat_sessions.list_for_user(uow.session, user_id)
            return [SessionView.model_validate(s) for s in sessions]


class CreateSessionUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, user_id: UUID, title: str) -> SessionView:
        async with self.uow as uow:
            session_obj = await uow.chat_sessions.create(
                uow.session, {"user_id": user_id, "title": title}
            )
            # So'nggi faollik: yangi suhbat ochildi
            await uow.login_events.create(
                uow.session, {"user_id": user_id, "action": "session"}
            )
            await uow.commit()
            return SessionView.model_validate(session_obj)


class GetSessionUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, user_id: UUID, session_id: UUID) -> SessionDetailView:
        async with self.uow as uow:
            s = await uow.chat_sessions.get_single(
                uow.session, id=session_id, user_id=user_id
            )
            if not s:
                raise InstanceNotFoundException(SESSION_NOT_FOUND)
            messages = await uow.chat_messages.list_by_session(uow.session, session_id)
            return SessionDetailView(
                id=s.id,
                title=s.title,
                created_at=s.created_at,
                updated_at=s.updated_at,
                messages=[MessageView.model_validate(m) for m in messages],
            )


class RenameSessionUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self, user_id: UUID, session_id: UUID, title: str
    ) -> SessionView:
        async with self.uow as uow:
            s = await uow.chat_sessions.get_single(
                uow.session, id=session_id, user_id=user_id
            )
            if not s:
                raise InstanceNotFoundException(SESSION_NOT_FOUND)
            s.title = title
            await uow.commit()
            return SessionView.model_validate(s)


class DeleteSessionUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, user_id: UUID, session_id: UUID) -> SuccessResponse:
        async with self.uow as uow:
            s = await uow.chat_sessions.get_single(
                uow.session, id=session_id, user_id=user_id
            )
            if not s:
                raise InstanceNotFoundException(SESSION_NOT_FOUND)
            await uow.chat_sessions.delete(uow.session, id=session_id)
            await uow.commit()
            return SuccessResponse(success=True)


class AddMessageUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self, user_id: UUID, session_id: UUID, data: AddMessageModel
    ) -> MessageView:
        async with self.uow as uow:
            s = await uow.chat_sessions.get_single(
                uow.session, id=session_id, user_id=user_id
            )
            if not s:
                raise InstanceNotFoundException(SESSION_NOT_FOUND)
            message = await uow.chat_messages.create(
                uow.session,
                {
                    "session_id": session_id,
                    "role": data.role,
                    "content": data.content,
                },
            )
            # Suhbatni ro'yxat tepasiga ko'tarish uchun updated_at yangilanadi
            s.updated_at = get_utc_now()
            await uow.commit()
            return MessageView.model_validate(message)


class VoteMessageUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self, user_id: UUID, session_id: UUID, message_id: UUID, vote: str | None
    ) -> MessageView:
        async with self.uow as uow:
            s = await uow.chat_sessions.get_single(
                uow.session, id=session_id, user_id=user_id
            )
            if not s:
                raise InstanceNotFoundException(SESSION_NOT_FOUND)
            msg = await uow.chat_messages.get_single(
                uow.session, id=message_id, session_id=session_id
            )
            if not msg:
                raise InstanceNotFoundException("Xabar topilmadi")
            msg.vote = vote
            await uow.commit()
            return MessageView.model_validate(msg)


# ---- DI factory'lar ----
def get_list_sessions_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> ListSessionsUseCase:
    return ListSessionsUseCase(uow=uow)


def get_create_session_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> CreateSessionUseCase:
    return CreateSessionUseCase(uow=uow)


def get_get_session_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> GetSessionUseCase:
    return GetSessionUseCase(uow=uow)


def get_rename_session_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> RenameSessionUseCase:
    return RenameSessionUseCase(uow=uow)


def get_delete_session_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> DeleteSessionUseCase:
    return DeleteSessionUseCase(uow=uow)


def get_add_message_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> AddMessageUseCase:
    return AddMessageUseCase(uow=uow)


def get_vote_message_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> VoteMessageUseCase:
    return VoteMessageUseCase(uow=uow)

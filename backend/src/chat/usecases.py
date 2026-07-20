from uuid import UUID

from fastapi import Depends

from loggers import get_logger
from src.core.ai.dependencies import get_ai_client
from src.core.ai.interfaces import BaseAIClient
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import InstanceNotFoundException
from src.core.schemas import SuccessResponse
from src.core.utils.datetime_utils import get_utc_now
from src.core.utils.uzbek_script import is_cyrillic_text, to_cyrillic
from src.chat.prompts import TITLE_SYSTEM
from src.chat.schemas import (
    AddMessageModel,
    GenerateTitleResult,
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
                is_pinned=s.is_pinned,
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


class PinSessionUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self, user_id: UUID, session_id: UUID, is_pinned: bool
    ) -> SessionView:
        async with self.uow as uow:
            s = await uow.chat_sessions.get_single(
                uow.session, id=session_id, user_id=user_id
            )
            if not s:
                raise InstanceNotFoundException(SESSION_NOT_FOUND)
            s.is_pinned = is_pinned
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


class GenerateTitleUseCase:
    """Birinchi xabar matnidan Qwen orqali qisqa suhbat sarlavhasi yasaydi
    (ChatGPT uslubida). DB'ga tegmaydi — faqat matn qaytaradi."""

    MAX_TOKENS = 32
    MAX_LEN = 60

    def __init__(self, ai_client: BaseAIClient) -> None:
        self.ai_client = ai_client

    async def execute(self, text: str) -> GenerateTitleResult:
        raw = await self.ai_client.generate_text(
            text,
            system_prompt=TITLE_SYSTEM,
            temperature=0.3,
            max_tokens=self.MAX_TOKENS,
        )
        title = raw.strip().strip('"').strip("'").strip()
        if not title:
            title = text.strip()[:42]
        if len(title) > self.MAX_LEN:
            title = title[: self.MAX_LEN].rstrip()
        # TITLE_SYSTEM sarlavhani doim lotincha yozadi — foydalanuvchi
        # kirillcha yozgan bo'lsa, sarlavhani ham shu alifboga o'giramiz.
        if is_cyrillic_text(text):
            title = to_cyrillic(title)
        return GenerateTitleResult(title=title)


class DeleteMessageUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self, user_id: UUID, session_id: UUID, message_id: UUID
    ) -> SuccessResponse:
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
            await uow.chat_messages.delete(uow.session, id=message_id)
            await uow.commit()
            return SuccessResponse(success=True)


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


def get_pin_session_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> PinSessionUseCase:
    return PinSessionUseCase(uow=uow)


def get_add_message_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> AddMessageUseCase:
    return AddMessageUseCase(uow=uow)


def get_vote_message_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> VoteMessageUseCase:
    return VoteMessageUseCase(uow=uow)


def get_delete_message_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> DeleteMessageUseCase:
    return DeleteMessageUseCase(uow=uow)


def get_generate_title_use_case(
    ai_client: BaseAIClient = Depends(get_ai_client),
) -> GenerateTitleUseCase:
    return GenerateTitleUseCase(ai_client=ai_client)

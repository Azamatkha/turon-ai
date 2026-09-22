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
from src.knowledge.schemas import ChatTurn
from src.chat.schemas import (
    AddMessageModel,
    GenerateTitleResult,
    MessageView,
    SessionDetailView,
    SessionView,
)

logger = get_logger(__name__)

SESSION_NOT_FOUND = "Suhbat topilmadi"

# Unli harflar — lotin va kirill. O'zbekcha va ruscha har bir so'zda kamida
# bitta unli bor, shuning uchun unlisiz "so'z" ("yyt", "qwrt") tasodifan
# bosilgan tugmalar deb qaraladi.
_VOWELS = frozenset("aeiouAEIOU" "аеёиоуўэюяыАЕЁИОУЎЭЮЯЫ")


def _looks_meaningless(text: str) -> bool:
    """Xabar ma'noli so'zdan iboratmi yoki tasodifiy belgilarmi.

    Ma'noli deb sanaladi: kamida ikki harfli va ichida unlisi bor bitta so'z
    ("uy", "meros", "кредит"). Raqamlar ("19") va unlisiz bo'laklar ("yyt")
    ma'noli so'z hisoblanmaydi.
    """
    for word in text.split():
        letters = [ch for ch in word if ch.isalpha()]
        if len(letters) >= 2 and any(ch in _VOWELS for ch in letters):
            return False
    return True


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
                translate_lang=s.translate_lang,
                created_at=s.created_at,
                updated_at=s.updated_at,
                messages=[MessageView.model_validate(m) for m in messages],
            )


class LoadHistoryUseCase:
    """Savol uchun suhbat tarixini BAZADAN o'qiydi.

    Ilgari tarixni faqat mijoz yuborardi. Mobil ilova uni yubormagani uchun
    "19" kabi qisqa savol kontekstsiz qolib, router uni "bankka aloqasi yo'q"
    deb rad etardi. Endi mijoz `session_id` bersa, tarixni backend o'zi yig'adi.
    """

    # Nechta oxirgi xabar olinadi. Router baribir oxirgi 6 almashuvni ishlatadi
    # (`QuestionRouter.HISTORY_TURNS`), bu esa zaxira bilan.
    MESSAGE_LIMIT = 20

    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self, user_id: UUID, session_id: UUID, question: str
    ) -> list[ChatTurn]:
        async with self.uow as uow:
            # Egalik tekshiruvi: birovning suhbati tarixi olinmasin
            s = await uow.chat_sessions.get_single(
                uow.session, id=session_id, user_id=user_id
            )
            if not s:
                raise InstanceNotFoundException(SESSION_NOT_FOUND)
            messages = await uow.chat_messages.list_by_session(uow.session, session_id)

        turns = [
            ChatTurn(role=m.role, content=m.content)
            for m in messages
            if m.content and m.content.strip()
        ]
        # Mijoz odatda savolni AVVAL saqlaydi, keyin /ask ga yuboradi — o'sha
        # savol tarixda ham turmasin (modelga ikki marta borardi).
        if (
            turns
            and turns[-1].role == "user"
            and turns[-1].content.strip() == question.strip()
        ):
            turns.pop()
        return turns[-self.MESSAGE_LIMIT :]


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
    # Ma'nosiz xabardan yasalgan sarlavha ham qisqa bo'lsin
    RAW_TITLE_LEN = 42

    def __init__(self, ai_client: BaseAIClient) -> None:
        self.ai_client = ai_client

    async def execute(self, text: str) -> GenerateTitleResult:
        # MA'NOSIZ XABARGA MODEL CHAQIRILMAYDI. Model bo'sh joyni har doim
        # "to'ldirib" beradi: "yyt" uchun "Yaponiyadagi yaponcha til haqida"
        # degan sarlavha yasab qo'ygan edi — foydalanuvchi yon panelda umuman
        # boshqa suhbatni ko'rgandek bo'ladi. Bunday xabarning O'ZI sarlavha
        # bo'lgani rost: u hech bo'lmasa yozilgan narsani ko'rsatadi.
        # Yon foyda: ortiqcha LLM chaqiruvi (~3 s) ham ketmaydi.
        if _looks_meaningless(text):
            return GenerateTitleResult(title=text.strip()[: self.RAW_TITLE_LEN])

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


def get_load_history_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> LoadHistoryUseCase:
    return LoadHistoryUseCase(uow=uow)


def get_generate_title_use_case(
    ai_client: BaseAIClient = Depends(get_ai_client),
) -> GenerateTitleUseCase:
    return GenerateTitleUseCase(ai_client=ai_client)

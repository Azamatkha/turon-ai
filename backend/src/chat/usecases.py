from dataclasses import dataclass
from datetime import timedelta
import re
from uuid import UUID

from fastapi import Depends

from loggers import get_logger
from src.chat.export_docx import ExportMessage, build_chat_docx
from src.chat.prompts import (
    SUGGEST_RU_OVERRIDE,
    SUGGEST_SYSTEM,
    TITLE_RU_OVERRIDE,
    TITLE_SYSTEM,
)
from src.chat.schemas import (
    AddMessageModel,
    GenerateTitleResult,
    MessageSearchHit,
    MessageView,
    SessionDetailView,
    SessionView,
    SuggestFollowupsRequest,
    SuggestFollowupsResult,
)
from src.core.ai.dependencies import get_ai_client
from src.core.ai.guard import looks_like_injection, mask_pii
from src.core.ai.interfaces import BaseAIClient
from src.core.database.session import async_session, get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol, get_uow
from src.core.errors.exceptions import InstanceNotFoundException
from src.core.schemas import SuccessResponse
from src.core.utils.datetime_utils import get_utc_now
from src.core.utils.uzbek_script import to_cyrillic, to_latin
from src.knowledge.lang import detect_reply_lang
from src.knowledge.schemas import ChatTurn
from src.main.config import config
from src.notifications.enums import NotificationType
from src.notifications.usecases import BroadcastNotificationUseCase
from src.user.enums import UserRole

logger = get_logger(__name__)


# ---- Savollar statistikasi (question_logs) ----

_NON_WORD = re.compile(r"[^\w\s']+")
_APOSTROPHES = re.compile(r"[ʻʼ‘’`´]")
_SPACES = re.compile(r"\s+")


def normalize_question(text: str) -> str:
    """Bir xil savollarni guruhlash kaliti: lotin, kichik harf, tinish
    belgisiz, bo'shliqlar bitta. "Kredit foizi qancha?" va "кредит фоизи
    қанча" bitta guruhga tushadi."""
    t = _APOSTROPHES.sub("'", to_latin(text).lower())
    t = _NON_WORD.sub(" ", t)
    return _SPACES.sub(" ", t).strip()[:300]


@dataclass
class QuestionLogEntry:
    user_id: UUID
    question: str
    intent: str | None
    # "answered" | "no_info" | "blocked" | "error"
    outcome: str
    top_score: float | None
    sources_count: int
    completion_tokens: int
    duration_ms: int
    # Veb-qidiruv javobi bo'lsa — sahifa havolalari
    source_urls: list[str] | None = None


async def log_question(entry: QuestionLogEntry) -> None:
    """Savolni statistikaga yozadi.

    Javob oqimi (StreamingResponse) tugagach chaqiriladi — so'rovning DI
    sessiyasi bu paytda yopilgan bo'lishi mumkin, shuning uchun o'z sessiyasi
    ochiladi. Xato bo'lsa faqat log: statistika foydalanuvchi javobini
    buzmasligi kerak.
    """
    # Statistikada ham karta/JShShIR/pasport ochiq saqlanmasin
    question = mask_pii(entry.question.strip())[0]
    if not question:
        return
    try:
        async with async_session() as session:
            uow = await get_uow(session)
            async with uow:
                await uow.question_logs.create(
                    uow.session,
                    {
                        "user_id": entry.user_id,
                        "question": question[:2000],
                        "normalized": normalize_question(question),
                        "intent": entry.intent,
                        "outcome": entry.outcome,
                        "top_score": entry.top_score,
                        "sources_count": entry.sources_count,
                        "completion_tokens": entry.completion_tokens,
                        "duration_ms": entry.duration_ms,
                        "source_urls": entry.source_urls or None,
                    },
                )
                await uow.commit()
    except Exception:  # noqa: BLE001 - statistika javobni buzmasin
        logger.exception("Savol statistikasini yozib bo'lmadi")

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
                    # Token statistikasi faqat assistant javobiga tegishli
                    "completion_tokens": (
                        data.completion_tokens if data.role == "assistant" else None
                    ),
                    "finish_reason": (
                        data.finish_reason if data.role == "assistant" else None
                    ),
                    "sources": (
                        [x.model_dump() for x in data.sources]
                        if data.role == "assistant" and data.sources
                        else None
                    ),
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

        # Uch holat: ruscha -> ruscha sarlavha; o'zbek kirill -> lotincha
        # yozib kirillga o'giramiz; o'zbek lotin -> o'zgarishsiz.
        # Ilgari faqat "kirillmi" tekshirilardi va ruscha xabar ham o'zbek
        # kirilliga aylanib qolardi.
        lang = detect_reply_lang(text, None)
        raw = await self.ai_client.generate_text(
            text,
            system_prompt=TITLE_SYSTEM + TITLE_RU_OVERRIDE if lang == "ru" else TITLE_SYSTEM,
            temperature=0.3,
            max_tokens=self.MAX_TOKENS,
        )
        title = raw.strip().strip('"').strip("'").strip()
        if not title:
            title = text.strip()[:42]
        if len(title) > self.MAX_LEN:
            title = title[: self.MAX_LEN].rstrip()
        if lang == "uz_cyrl":
            title = to_cyrillic(title)
        return GenerateTitleResult(title=title)


_BULLET = re.compile(r"^\s*(?:[-*•–]|\d+[.)])\s*")


def _clean_suggestions(raw: str, question: str, limit: int = 3) -> list[str]:
    """Model javobidan savollar ro'yxati: raqam/tirnoq olib tashlanadi,
    juda qisqa/uzunlari, takrorlar va asl savolning o'zi tashlanadi."""
    seen = {normalize_question(question)}
    out: list[str] = []
    for line in raw.splitlines():
        q = _BULLET.sub("", line).strip().strip('"').strip("'").strip("«»").strip()
        if not q or len(q) < 8 or len(q) > 90:
            continue
        if not q.endswith("?"):
            q = q.rstrip(".!") + "?"
        key = normalize_question(q)
        if key in seen:
            continue
        seen.add(key)
        out.append(q)
        if len(out) == limit:
            break
    return out


class SuggestFollowupsUseCase:
    """Javobdan keyin 3 ta "keyingi savol" taklifi (chip).

    Javob oqimidan ALOHIDA chaqiriladi — foydalanuvchi javobni kutib
    qolmaydi, takliflar keyinroq paydo bo'ladi. Qisqa chaqiruv: past
    max_tokens, javob matni qisqartiriladi.
    """

    MAX_TOKENS = 120
    ANSWER_CHARS = 1500

    def __init__(self, ai_client: BaseAIClient) -> None:
        self.ai_client = ai_client

    async def execute(self, data: SuggestFollowupsRequest) -> SuggestFollowupsResult:
        if (
            not config.ai.FOLLOWUP_SUGGESTIONS_ENABLED
            or _looks_meaningless(data.question)
            or looks_like_injection(data.question)
        ):
            return SuggestFollowupsResult(suggestions=[])
        lang = detect_reply_lang(data.question, None)
        question = mask_pii(data.question)[0]
        answer = mask_pii(data.answer[: self.ANSWER_CHARS])[0]
        sources = ", ".join(s.strip() for s in data.sources if s.strip())[:400]
        prompt = f"QUESTION: {question}\n\nANSWER: {answer}"
        if sources:
            prompt += f"\n\nSOURCE DOCUMENTS: {sources}"
        try:
            raw = await self.ai_client.generate_text(
                prompt,
                system_prompt=SUGGEST_SYSTEM + SUGGEST_RU_OVERRIDE if lang == "ru" else SUGGEST_SYSTEM,
                temperature=0.4,
                max_tokens=self.MAX_TOKENS,
            )
        except Exception:  # noqa: BLE001 - taklif ixtiyoriy, xato chatni buzmasin
            logger.warning("Keyingi savol takliflarini olib bo'lmadi", exc_info=True)
            return SuggestFollowupsResult(suggestions=[])
        items = _clean_suggestions(raw, data.question)
        if lang == "uz_cyrl":
            items = [to_cyrillic(q) for q in items]
        return SuggestFollowupsResult(suggestions=items)


SEARCH_MIN_LEN = 2
SNIPPET_RADIUS = 60


def _like_pattern(term: str) -> str:
    """LIKE uchun xavfsiz naqsh: %, _ va \\ belgilarini ekranlaydi."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _snippet(text: str, terms: list[str]) -> str:
    """Birinchi moslik atrofidagi ~120 belgilik parcha (bir qatorga)."""
    flat = " ".join(text.split())
    low = flat.lower()
    pos = min((i for t in terms if (i := low.find(t.lower())) >= 0), default=-1)
    if pos < 0:
        return flat[: SNIPPET_RADIUS * 2] + ("…" if len(flat) > SNIPPET_RADIUS * 2 else "")
    start = max(0, pos - SNIPPET_RADIUS)
    end = min(len(flat), pos + SNIPPET_RADIUS)
    return ("…" if start > 0 else "") + flat[start:end] + ("…" if end < len(flat) else "")


class SearchMessagesUseCase:
    """Chat tarixida matn bo'yicha qidiruv (faqat o'z suhbatlarida).

    O'zbek matni lotin ham, kirill ham bo'lishi mumkin — so'rov ikkala
    yozuvda qidiriladi: "kredit" "кредит"ni ham topadi va aksincha.
    """

    LIMIT = 30

    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, user_id: UUID, q: str) -> list[MessageSearchHit]:
        term = " ".join(q.split())[:100]
        if len(term) < SEARCH_MIN_LEN:
            return []
        terms = list(dict.fromkeys([term, to_latin(term), to_cyrillic(term)]))
        async with self.uow as uow:
            rows = await uow.chat_sessions.search_messages(
                uow.session,
                user_id=user_id,
                patterns=[_like_pattern(t) for t in terms],
                limit=self.LIMIT,
            )
        return [
            MessageSearchHit(
                session_id=msg.session_id,
                session_title=title,
                message_id=msg.id,
                role=msg.role,
                snippet=_snippet(msg.content, terms),
                created_at=msg.created_at,
            )
            for msg, title in rows
        ]


# Eksport faylidagi yorliqlar — interfeys tili bo'yicha
_EXPORT_LABELS = {
    "uz": ("Siz", "Turon AI", "Eksport qilingan sana"),
    "uz_cyrl": ("Сиз", "Turon AI", "Экспорт қилинган сана"),
    "ru": ("Вы", "Turon AI", "Дата экспорта"),
}


@dataclass
class ExportedFile:
    filename: str
    content: bytes


class ExportSessionDocxUseCase:
    """Suhbatni .docx faylga eksport (faqat o'z suhbati)."""

    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, user_id: UUID, session_id: UUID, lang: str) -> ExportedFile:
        async with self.uow as uow:
            s = await uow.chat_sessions.get_single(uow.session, id=session_id, user_id=user_id)
            if not s:
                raise InstanceNotFoundException(SESSION_NOT_FOUND)
            messages = await uow.chat_messages.list_by_session(uow.session, session_id)
            title = s.title or "Turon AI"
        user_label, bot_label, date_label = _EXPORT_LABELS.get(lang, _EXPORT_LABELS["uz"])
        # Sana Toshkent vaqtida (UTC+5) — xodim faylda o'z soatini ko'rsin
        tz_shift = timedelta(hours=5)
        content = build_chat_docx(
            title,
            [
                ExportMessage(
                    role=m.role,
                    content=m.content,
                    created_at=(m.created_at + tz_shift) if m.created_at else None,
                )
                for m in messages
            ],
            user_label=user_label,
            bot_label=bot_label,
            meta_line=f"{date_label}: {(get_utc_now() + tz_shift).strftime('%d.%m.%Y %H:%M')}",
        )
        # Fayl nomida taqiqlangan belgilar olib tashlanadi, bo'shliqlar bitta
        safe = " ".join(re.sub(r'[\\/:*?"<>|\x00-\x1f]+', " ", title).split())[:80] or "Turon AI"
        return ExportedFile(filename=f"{safe}.docx", content=content)


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
        self,
        user_id: UUID,
        session_id: UUID,
        message_id: UUID,
        vote: str | None,
        reason: str | None = None,
        comment: str | None = None,
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
            # Sabab faqat dislike'da saqlanadi. Har yangi baho admin navbatiga
            # qaytadan tushadi (vote_reviewed=False).
            if vote == "down":
                msg.vote_reason = reason
                msg.vote_comment = (comment or "").strip() or None
            else:
                msg.vote_reason = None
                msg.vote_comment = None
            msg.vote_reviewed = False
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


def get_suggest_followups_use_case(
    ai_client: BaseAIClient = Depends(get_ai_client),
) -> SuggestFollowupsUseCase:
    return SuggestFollowupsUseCase(ai_client=ai_client)


def get_search_messages_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> SearchMessagesUseCase:
    return SearchMessagesUseCase(uow=uow)


def get_export_session_docx_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> ExportSessionDocxUseCase:
    return ExportSessionDocxUseCase(uow=uow)


# ---- Xavfli so'rovlar: adminga bildirishnoma ----

# Bildirishnomada savolning shuncha belgisi ko'rinadi (to'liq matn — admin panelda)
_FLAG_SNIPPET = 120


async def notify_safety_flag(username: str, question: str, kind: str) -> None:
    """Xavfli so'rov / so'kinish haqida ADMINLARGA bildirishnoma.

    Javob oqimi tugagach chaqiriladi — o'z sessiyasi bilan (log_question kabi).
    Shaxsiy ma'lumot (karta, JShShIR) bildirishnomaga ham maskalangan holda
    tushadi. Xato bo'lsa faqat log: foydalanuvchi javobi buzilmasin.
    """
    snippet = " ".join(mask_pii(question)[0].split())
    if len(snippet) > _FLAG_SNIPPET:
        snippet = snippet[:_FLAG_SNIPPET].rstrip() + "…"
    try:
        async with async_session() as session:
            uow = await get_uow(session)
            await BroadcastNotificationUseCase(uow).execute(
                NotificationType.SAFETY_FLAGGED,
                params={"title": f"@{username}: {snippet}", "kind": kind},
                role=UserRole.ADMIN,
            )
    except Exception:  # noqa: BLE001
        logger.exception("Xavfli so'rov haqida bildirishnoma yuborilmadi")

"""Tarjimon rejimi.

Oqim:
    /translate          -> til so'raladi (holat: "pending")
    "2" / "ruscha"      -> til tanlanadi (holat: "ru")
    <har qanday matn>   -> shu tilga tarjima qilinadi
    /stop               -> rejim o'chadi (holat: None)

`/translate ru` — til darhol tanlanadi. Rejim yoqilgan paytda yana
`/translate` yozilsa — tilni almashtirish uchun qayta so'raladi.

Holat `chat_sessions.translate_lang` da turadi, shuning uchun rejim faqat
`session_id` bilan kelgan so'rovda ishlaydi. Tarjima yo'lida router ham,
Qdrant ham chaqirilmaydi — bank-bot mantiqiga umuman tegmaydi.
"""

import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import Depends

from loggers import get_logger
from src.chat.usecases import SESSION_NOT_FOUND
from src.core.ai.dependencies import get_ai_client
from src.core.ai.interfaces import BaseAIClient
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import InstanceNotFoundException
from src.core.utils.uzbek_script import (
    StreamingScriptFixer,
    StreamingTransliterator,
    fix_mixed_script,
    is_cyrillic_text,
    to_cyrillic,
    to_latin,
)
from src.knowledge.schemas import AnswerResult
from src.translator.prompts import translate_system

logger = get_logger(__name__)

PENDING = "pending"

# Ro'yxatdagi tartib — foydalanuvchi raqam bilan tanlaydi ("2" -> ruscha)
LANGUAGES: list[tuple[str, str]] = [
    ("en", "Inglizcha"),
    ("ru", "Ruscha"),
    ("uz", "O'zbekcha (lotin)"),
    ("uz_cyrl", "O'zbekcha (kirill)"),
]
_LANG_LABELS = dict(LANGUAGES)

_START_COMMANDS = frozenset({"/translate", "/tarjima"})
_STOP_COMMANDS = frozenset({"/stop", "/exit"})

# Til nomini tanish: so'z o'zagi bo'yicha, lotinga keltirilgan matnda
# ("русский" -> "russkij", "ўзбекча" -> "o'zbekcha"). Tartib muhim: kirill
# birinchi — "o'zbek kirill" o'zbek lotin emas.
_LANG_STEMS: list[tuple[str, tuple[str, ...], frozenset[str]]] = [
    ("uz_cyrl", ("kiril", "kril", "cyril", "cyrl"), frozenset()),
    ("en", ("ingliz", "engl", "angl"), frozenset({"en", "eng"})),
    ("ru", ("rus",), frozenset({"ru"})),
    ("uz", ("o'zbek", "ozbek", "uzbek", "lotin"), frozenset({"uz", "uzb"})),
]
_COMMAND_RE = re.compile(r"(/[a-z]+)")
_APOSTROPHES = dict.fromkeys(map(ord, "‘’ʻʼ`´"), "'")
# Uzun matn tanlov emas — pending holatida oddiy gapni til deb o'qib
# yubormaslik uchun ("rus tilida gapiradigan mijoz keldi" -> ruscha EMAS).
_MAX_CHOICE_WORDS = 4

TEMPERATURE = 0.1
MAX_TOKENS = 2048
# ~1300 token kirish; javob ham shuncha — MAX_TOKENS ga sig'adi.
MAX_TEXT_CHARS = 4000


def _language_menu() -> str:
    return "\n".join(f"{i}. {label}" for i, (_, label) in enumerate(LANGUAGES, 1))


ASK_LANGUAGE = (
    "Tarjimon rejimi. Qaysi tilga tarjima qilay?\n"
    f"{_language_menu()}\n"
    "Raqamini yoki til nomini yozing. Chiqish uchun: /stop"
)
ASK_LANGUAGE_AGAIN = (
    "Tilni tushunmadim. Quyidagilardan birini tanlang:\n"
    f"{_language_menu()}\n"
    "Tarjimon rejimidan chiqish uchun: /stop"
)
ENABLED = (
    "Tayyor. Tarjima tili: {label}.\n"
    "Endi istalgan matnni yozing — tarjimasini qaytaraman.\n"
    "Tilni almashtirish: /translate, chiqish: /stop"
)
DISABLED = "Tarjimon rejimi o'chirildi. Savollaringizga bank yordamchisi sifatida javob beraman."
NOT_ACTIVE = "Tarjimon rejimi yoqilmagan. Yoqish uchun: /translate"
NO_SESSION = (
    "Tarjimon rejimi faqat suhbat ichida ishlaydi. Yangi suhbat ochib, "
    "qaytadan /translate deb yozing."
)
TOO_LONG = (
    "Matn juda uzun ({size} belgi). Bir martada {limit} belgigacha tarjima "
    "qilaman — matnni bo'laklab yuboring."
)


def _norm(text: str) -> str:
    return to_latin(text).translate(_APOSTROPHES).lower().strip()


def _parse_command(text: str) -> tuple[str | None, str]:
    """("start" | "stop" | None, buyruqdan keyingi qism)."""
    stripped = text.strip()
    if not stripped.startswith("/"):
        return None, ""
    head, _, rest = stripped.partition(" ")
    head = head.lower()
    if head in _START_COMMANDS:
        return "start", rest.strip()
    if head in _STOP_COMMANDS:
        return "stop", rest.strip()
    return None, ""


def parse_language(text: str) -> str | None:
    """Foydalanuvchi javobidan til kodini aniqlaydi: "2", "ruscha", "english",
    "o'zbek kirill", "русский". Topilmasa — None."""
    words = re.findall(r"[a-z0-9']+", _norm(text))
    if not words or len(words) > _MAX_CHOICE_WORDS:
        return None
    if len(words) == 1 and words[0].isdigit():
        index = int(words[0])
        return LANGUAGES[index - 1][0] if 1 <= index <= len(LANGUAGES) else None
    for code, stems, exact in _LANG_STEMS:
        if any(w in exact or w.startswith(stems) for w in words):
            return code
    return None


@dataclass(frozen=True)
class TranslatorStep:
    """`prepare` natijasi: yo tayyor javob (`reply`), yo tarjima vazifasi."""

    cyrillic: bool  # bot matnlari foydalanuvchi alifbosida qaytadi
    reply: str | None = None
    target: str | None = None
    text: str = ""


class TranslatorUseCase:
    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
        ai_client: BaseAIClient,
    ) -> None:
        self.uow = uow
        self.ai_client = ai_client

    async def prepare(
        self, user_id: UUID, session_id: UUID | None, question: str
    ) -> TranslatorStep | None:
        """Savol tarjimonga tegishlimi. None — yo'q, oddiy bank-bot javob beradi.

        Holat o'zgarishi (yoqish/til tanlash/o'chirish) shu yerda bazaga
        yoziladi — javob oqimi boshlanishidan OLDIN, xato bo'lsa klient
        uni oddiy HTTP xatosi sifatida olishi uchun."""
        cyrillic = is_cyrillic_text(question)
        command, arg = _parse_command(question)

        if session_id is None:
            # Veb/mobil sessiyasiz so'rov: holatni saqlashga joy yo'q
            if command is None:
                return None
            return TranslatorStep(cyrillic=cyrillic, reply=NO_SESSION)

        async with self.uow as uow:
            s = await uow.chat_sessions.get_single(
                uow.session, id=session_id, user_id=user_id
            )
            if not s:
                raise InstanceNotFoundException(SESSION_NOT_FOUND)
            state = s.translate_lang

            if command == "start":
                lang = parse_language(arg) if arg else None
                s.translate_lang = lang or PENDING
                await uow.commit()
                reply = ENABLED.format(label=_LANG_LABELS[lang]) if lang else ASK_LANGUAGE
                return TranslatorStep(cyrillic=cyrillic, reply=reply)

            if command == "stop":
                if state is None:
                    return TranslatorStep(cyrillic=cyrillic, reply=NOT_ACTIVE)
                s.translate_lang = None
                await uow.commit()
                return TranslatorStep(cyrillic=cyrillic, reply=DISABLED)

            if state is None:
                return None

            if state == PENDING:
                lang = parse_language(question)
                if lang is None:
                    return TranslatorStep(cyrillic=cyrillic, reply=ASK_LANGUAGE_AGAIN)
                s.translate_lang = lang
                await uow.commit()
                return TranslatorStep(
                    cyrillic=cyrillic,
                    reply=ENABLED.format(label=_LANG_LABELS[lang]),
                )

        # Rejim yoqilgan — matn tarjima qilinadi
        text = question.strip()
        if len(text) > MAX_TEXT_CHARS:
            return TranslatorStep(
                cyrillic=cyrillic,
                reply=TOO_LONG.format(size=len(text), limit=MAX_TEXT_CHARS),
            )
        return TranslatorStep(cyrillic=cyrillic, target=state, text=text)

    @staticmethod
    def _reply_text(step: TranslatorStep) -> str:
        reply = step.reply or ""
        if not step.cyrillic:
            return reply
        # Buyruqlar ("/translate", "/stop") o'girilmaydi — aks holda
        # "/транслате" chiqib, foydalanuvchi uni yozsa ishlamasdi.
        parts = _COMMAND_RE.split(reply)
        return "".join(p if _COMMAND_RE.fullmatch(p) else to_cyrillic(p) for p in parts)

    async def stream(self, step: TranslatorStep) -> AsyncIterator[dict[str, Any]]:
        """`/ask/stream` bilan bir xil hodisalar: delta... va oxirida done."""
        if step.target is None:
            yield {"type": "delta", "text": self._reply_text(step)}
            yield {
                "type": "done",
                "completion_tokens": 0,
                "finish_reason": "stop",
                "max_tokens": MAX_TOKENS,
                "sources": [],
            }
            return

        # Kirill: model lotincha yozadi, kod o'giradi. Lotin: model ba'zan
        # so'z ichida alifbolarni aralashtiradi — tuzatamiz.
        tr = StreamingTransliterator() if step.target == "uz_cyrl" else None
        sf = StreamingScriptFixer() if step.target == "uz" else None
        async for ev in self.ai_client.stream_generate(
            step.text,
            system_prompt=translate_system(step.target),
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        ):
            if ev.get("type") == "delta":
                text = ev["text"]
                if tr is not None:
                    text = tr.feed(text)
                elif sf is not None:
                    text = sf.feed(text)
                if not text:
                    continue
                ev = {**ev, "text": text}
            if ev.get("type") == "done":
                rest = ""
                if tr is not None:
                    rest = tr.flush()
                elif sf is not None:
                    rest = sf.flush()
                if rest:
                    yield {"type": "delta", "text": rest}
                ev["max_tokens"] = MAX_TOKENS
                ev["sources"] = []
            yield ev

    async def answer(self, step: TranslatorStep) -> AnswerResult:
        """`/ask` (oqimsiz) uchun."""
        if step.target is None:
            return AnswerResult(
                answer=self._reply_text(step),
                sources=[],
                finish_reason="stop",
                completion_tokens=0,
                max_tokens=MAX_TOKENS,
            )
        gen = await self.ai_client.generate_text_with_usage(
            step.text,
            system_prompt=translate_system(step.target),
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        text = gen.text.strip()
        if step.target == "uz_cyrl":
            text = to_cyrillic(text)
        elif step.target == "uz":
            text = fix_mixed_script(text)
        return AnswerResult(
            answer=text,
            sources=[],
            finish_reason=gen.finish_reason,
            completion_tokens=gen.completion_tokens,
            max_tokens=MAX_TOKENS,
        )


def get_translator_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
    ai_client: BaseAIClient = Depends(get_ai_client),
) -> TranslatorUseCase:
    return TranslatorUseCase(uow=uow, ai_client=ai_client)

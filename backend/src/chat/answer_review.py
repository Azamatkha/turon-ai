"""Javob berilgandan KEYIN fonda AI tahlili — admin "Savollar tahlili"da ko'radi.

Asosiy oqimdagi tekshiruv (knowledge/verifier.py) ba'zi javoblarni umuman
tekshirmaydi: xodim ma'lumotnomasi, "topilmadi", salomlashish va boshqa tayyor
(kod tuzgan) javoblar. Ular foydalanuvchiga kechiktirilmasdan chiqishi kerak va
rad etilganda qayta yozib bo'lmaydi (kod tuzgan javobni model "tuzatib" soxta
xodim to'qigan edi). Lekin admin aynan shu javoblarni ham ko'rishi kerak:
"IP ni qanday qo'shsam bo'ladi" savoliga "xodim topilmadi" berilgani hech
qayerda ko'rinmagan (2026-11-19).

Shuning uchun bunday javob jurnalga yozilgach, o'sha model uni FONDA baholaydi
va natija (`verdict`: ok | doubt, `verdict_note`: o'zbekcha tahlil) shu
yozuvga qo'shiladi. Foydalanuvchi javobi kutmaydi va o'zgarmaydi.
"""

import asyncio
from uuid import UUID

from loggers import get_logger
from src.core.ai.interfaces import BaseAIClient
from src.core.database.session import async_session
from src.core.database.uow import get_uow
from src.knowledge.schemas import ChatTurn
from src.knowledge.verifier import verify_answer
from src.main.config import config

logger = get_logger(__name__)

# Tahlil qilinadigan natijalar. "blocked"/"flagged" (xavfsizlik) va "error"
# — baholanadigan javob yo'q.
_REVIEWED_OUTCOMES = frozenset({"answered", "no_info", "web"})

# Fon vazifalari GC tomonidan yig'ib olinmasligi uchun kuchli havola
_tasks: set[asyncio.Task[None]] = set()


def needs_review(outcome: str, verdict: str | None, answer: str | None) -> bool:
    """Asosiy oqimda baholanmagan (verdict yo'q) va baholanadigan javob."""
    return (
        bool(config.ai.ANSWER_VERIFY)
        and verdict is None
        and outcome in _REVIEWED_OUTCOMES
        and bool((answer or "").strip())
    )


def schedule_review(
    log_id: UUID | None,
    ai_client: BaseAIClient,
    question: str,
    answer: str,
    history: list[ChatTurn] | None,
    interpreted: str | None,
) -> None:
    """Tahlilni fonda boshlaydi (javob oqimini kutdirmaydi)."""
    if log_id is None:
        return
    task = asyncio.create_task(
        review_answer(log_id, ai_client, question, answer, history, interpreted)
    )
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def review_answer(
    log_id: UUID,
    ai_client: BaseAIClient,
    question: str,
    answer: str,
    history: list[ChatTurn] | None,
    interpreted: str | None,
) -> None:
    v = await verify_answer(
        ai_client, question, answer, history, interpreted=interpreted
    )
    if v is None:
        verdict, note = "unchecked", None
    else:
        # "doubt" — AI javobni savolga mos emas deb topdi, lekin javob
        # foydalanuvchiga allaqachon chiqqan (qayta yozilmaydi).
        verdict = "ok" if v.ok else "doubt"
        note = v.analysis or v.problem or None
    try:
        async with async_session() as session:
            uow = await get_uow(session)
            async with uow:
                await uow.question_logs.update(
                    uow.session, {"verdict": verdict, "verdict_note": note}, id=log_id
                )
                await uow.commit()
    except Exception:  # noqa: BLE001 - tahlil foydalanuvchiga ta'sir qilmasin
        logger.exception("Javob tahlilini jurnalga yozib bo'lmadi: %s", log_id)

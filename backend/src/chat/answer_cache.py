"""Tez-tez beriladigan savollar uchun javob keshi (Redis).

Bir xil savol ("Kredit foizi qancha?") kuniga o'nlab marta keladi va har
safar model qaytadan ~10-30 soniya ishlaydi. Kesh shunday savolga
javobni darhol qaytaradi va GPU'ni bo'shatadi.

FAQAT XAVFSIZ HOLATLAR keshlanadi:
- suhbatning BIRINCHI savoli (tarix bo'lsa javob kontekstga bog'liq);
- niyat: mahsulot, umumiy tushuncha, filial (CACHEABLE_INTENTS). Xodimlar
  ma'lumotnomasi (shaxsiy ma'lumot, tez o'zgaradi), valyuta kursi (vaqtga
  bog'liq), salomlashish (baribir modelsiz) keshlanmaydi;
- javob topilgan va to'liq yozilgan (finish_reason == "stop");
- savolda shaxsiy ma'lumot (karta, JShShIR...) YO'Q.

Kalit: model + javob tili + normallashtirilgan savol + bilim bazasi
versiyasi. Baza o'zgarsa versiya oshadi — eski javoblar ishlatilmaydi.
"""

from collections.abc import AsyncIterator
from datetime import timedelta
import hashlib
import json
from typing import Any

from redis.asyncio import Redis

from loggers import get_logger
from src.chat.usecases import normalize_question
from src.core.ai.guard import mask_pii
from src.core.utils.datetime_utils import get_utc_now
from src.core.vectorstore.version import get_kb_version
from src.knowledge.lang import detect_reply_lang
from src.knowledge.schemas import ChatTurn
from src.knowledge.usecases import AnswerQuestionUseCase
from src.main.config import config

logger = get_logger(__name__)

CACHEABLE_INTENTS = frozenset({"product", "concept", "branch"})
# Javob mantig'i yoki promptlar jiddiy o'zgarsa — versiyani oshiring:
# eski keshlangan javoblar o'z-o'zidan ishlatilmay qoladi.
# v2: veb-qidiruv (concept savoli "cbu.uz'ni tekshiring" deb keshlangan edi)
KEY_PREFIX = "answer-cache:v2"
STATS_PREFIX = "answer-cache:stats"
# Keshdan javob "oqim" bo'lib keladi — frontend odatdagidek ko'rsatsin
_REPLAY_CHUNK = 400
# Done hodisasidagi to'xtash sababi: frontend "keshdan" belgisini shundan biladi
CACHED_FINISH_REASON = "cached"


def _day_key(kind: str, day: str | None = None) -> str:
    return f"{STATS_PREFIX}:{kind}:{day or (get_utc_now() + timedelta(hours=5)).strftime('%Y%m%d')}"


async def cache_key(redis: Redis, question: str, lang: str) -> str | None:
    """Kesh kaliti yoki None (bu savol keshlanmaydi)."""
    if mask_pii(question)[1]:
        return None
    norm = normalize_question(question)
    if len(norm) < 3:
        return None
    version = await get_kb_version(redis)
    # Veb-qidiruv yoqilishi/o'chirilishi javobni o'zgartiradi — kalitga kiradi
    web = int(config.web_search.WEB_SEARCH_ENABLED)
    digest = hashlib.sha256(f"{config.ai.OLLAMA_MODEL}|{lang}|web{web}|{norm}".encode()).hexdigest()[:32]
    return f"{KEY_PREFIX}:{version}:{digest}"


async def _count(redis: Redis, kind: str) -> None:
    try:
        key = _day_key(kind)
        await redis.incr(key)
        await redis.expire(key, 8 * 86400)
    except Exception:  # noqa: BLE001 - statistika ixtiyoriy
        pass


async def cache_stats_today(redis: Redis) -> tuple[int, int]:
    """(keshdan berilgan, keshlanadigan lekin modeldan olingan) — bugun."""
    hits, misses = await redis.get(_day_key("hits")), await redis.get(_day_key("misses"))
    return int(hits or 0), int(misses or 0)


async def cached_answer_stream(
    use_case: AnswerQuestionUseCase,
    question: str,
    history: list[ChatTurn] | None,
    redis: Redis,
) -> AsyncIterator[dict[str, Any]]:
    """`use_case.execute_stream` ustidan kesh qatlami.

    Keshda bo'lsa — model chaqirilmaydi, javob oqim ko'rinishida qaytariladi
    (`use_case.last_*` ham to'ldiriladi — savollar statistikasi to'g'ri
    yozilsin). Bo'lmasa — odatdagi oqim, oxirida shartlar mos bo'lsa keshga
    yoziladi.
    """
    key: str | None = None
    if config.ai.ANSWER_CACHE_ENABLED and not history:
        try:
            key = await cache_key(redis, question, detect_reply_lang(question, None))
            raw = await redis.get(key) if key else None
        except Exception:  # noqa: BLE001 - Redis yiqilsa ham javob berilsin
            logger.warning("Javob keshini o'qib bo'lmadi", exc_info=True)
            key, raw = None, None
        if raw:
            data = json.loads(raw)
            use_case.last_intent = data.get("intent")
            use_case.last_outcome = "answered"
            use_case.last_top_score = data.get("top_score")
            yield {"type": "status", "step": "analyze"}
            text = str(data.get("text", ""))
            for i in range(0, len(text), _REPLAY_CHUNK):
                yield {"type": "delta", "text": text[i : i + _REPLAY_CHUNK]}
            yield {
                "type": "done",
                "completion_tokens": 0,
                "finish_reason": CACHED_FINISH_REASON,
                "max_tokens": 0,
                "sources": data.get("sources") or [],
            }
            await _count(redis, "hits")
            return

    parts: list[str] = []
    done: dict[str, Any] | None = None
    async for ev in use_case.execute_stream(question=question, history=history):
        if ev.get("type") == "delta":
            parts.append(str(ev.get("text", "")))
        elif ev.get("type") == "done":
            done = ev
        yield ev

    if not key or done is None:
        return
    text = "".join(parts)
    if (
        use_case.last_outcome == "answered"
        and use_case.last_intent in CACHEABLE_INTENTS
        and done.get("finish_reason") == "stop"
        and text.strip()
    ):
        try:
            await redis.set(
                key,
                json.dumps(
                    {
                        "text": text,
                        "sources": done.get("sources") or [],
                        "intent": use_case.last_intent,
                        "top_score": use_case.last_top_score,
                    },
                    ensure_ascii=False,
                ),
                ex=config.ai.ANSWER_CACHE_TTL_HOURS * 3600,
            )
            await _count(redis, "misses")
        except Exception:  # noqa: BLE001
            logger.warning("Javobni keshga yozib bo'lmadi", exc_info=True)

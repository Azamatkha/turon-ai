"""Bilim bazasi "versiyasi" — Qdrant'dagi har qanday o'zgarishda oshadi.

Javob keshi (src/chat/answer_cache.py) kalitiga shu raqam qo'shiladi:
hujjat qo'shilsa, tahrirlansa, o'chirilsa yoki muddati o'zgarsa — versiya
oshadi va eski keshlangan javoblar o'z-o'zidan ishlatilmay qoladi (TTL
bilan tozalanadi). Shuning uchun keshni qo'lda tozalash shart emas.

O'zgarish QdrantStore'ning yozuvchi metodlarida qayd etiladi — bitta
markaziy joy, hech qaysi yuklash yo'li (veb, Celery, scraping) chetda qolmaydi.
"""

from redis.asyncio import Redis

from loggers import get_logger
from src.core.redis.core import create_redis_client
from src.main.config import config

logger = get_logger(__name__)

KB_VERSION_KEY = "kb:version"

_client: Redis | None = None


def _redis() -> Redis:
    global _client
    if _client is None:
        _client = create_redis_client(config.redis.dsn)
    return _client


async def bump_kb_version() -> None:
    """Versiyani oshiradi. Redis ishlamasa — faqat log: bilim bazasiga yozish
    to'xtamasligi kerak (eng yomon holda kesh TTL tugaguncha eski qoladi)."""
    try:
        await _redis().incr(KB_VERSION_KEY)
    except Exception:  # noqa: BLE001
        logger.warning("Bilim bazasi versiyasini oshirib bo'lmadi", exc_info=True)


async def get_kb_version(redis: Redis) -> str:
    value = await redis.get(KB_VERSION_KEY)
    if isinstance(value, bytes):
        value = value.decode()
    return str(value or "0")

"""EDO login/parol tekshiruvi — Turon ID (SSO) orqali ochilgan akkauntlar uchun.

EDO orqali yaratilgan userning bizdagi paroli tasodifiy (uni hech kim
bilmaydi). Shunday user mobil ilovaga yoki saytdagi login sahifasiga EDO'dagi
login/parolini yozsa, parol bizning bazadan o'tmaydi — shunda u Turon ID
bazasidan tekshiriladi. EDO tasdiqlasa, shu parol userning bizdagi paroli
qilib saqlanadi (login.py) — keyingi kirishlar Turon ID'siz o'tadi.

Turon ID'da buning uchun API yo'q, bazasi esa bizning server bilan bir joyda.
Shuning uchun uning Postgres'iga FAQAT O'QISH uchun ulanib, login bo'yicha
`password_hash` olinadi va bcrypt (`$2y$…`) bilan solishtiriladi. Hech narsa
yozilmaydi.

`EDO_LOGIN_DB_URL` bo'sh bo'lsa, tekshiruv O'CHIQ: har qanday parol rad
etiladi (sozlanguncha "hamma kiraveradi" holati bo'lmasin).

Baza javob bermasa — `InfrastructureException` (500): foydalanuvchi "parol
noto'g'ri" deb adashtirilmaydi, "keyinroq urinib ko'ring" ko'radi.
"""

import asyncio

import bcrypt
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from loggers import get_logger
from src.core.errors.exceptions import InfrastructureException
from src.main.config import config

logger = get_logger(__name__)

_engine: AsyncEngine | None = None


def edo_login_enabled() -> bool:
    return bool(config.edo_login.EDO_LOGIN_DB_URL)


def _get_engine() -> AsyncEngine:
    # Alohida, kichik pool: asosiy bazaning pool'iga aralashmaydi
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            config.edo_login.EDO_LOGIN_DB_URL,
            pool_size=2,
            max_overflow=3,
            pool_timeout=config.edo_login.EDO_LOGIN_TIMEOUT_SECONDS,
            pool_recycle=60 * 30,
        )
    return _engine


async def _fetch_hash(username: str) -> str | None:
    # Login registrsiz solishtiriladi (bizdagi `get_by_username` kabi).
    # Jadval nomi config'da tekshirilgan (faqat harf/raqam/_), ustunlar qat'iy.
    query = text(
        f"SELECT password_hash FROM {config.edo_login.EDO_LOGIN_USERS_TABLE} "
        "WHERE lower(username) = lower(:username) LIMIT 1"
    )
    try:
        async with _get_engine().connect() as conn:
            row = (await conn.execute(query, {"username": username.strip()})).first()
    except (SQLAlchemyError, OSError) as exc:
        logger.error("[EdoLogin] Turon ID bazasiga ulanib bo'lmadi: %r", exc)
        raise InfrastructureException("EDO tizimi javob bermadi") from exc
    return row[0] if row and row[0] else None


def _bcrypt_matches(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # bcrypt bo'lmagan hash — bu user bizdan tekshirilmaydi
        logger.warning("[EdoLogin] password_hash bcrypt emas, rad etildi.")
        return False


async def check_edo_password(username: str, password: str) -> bool:
    """Turon ID bazasida shu login/parol to'g'rimi. Sozlanmagan bo'lsa — doim False."""
    if not edo_login_enabled():
        return False
    password_hash = await _fetch_hash(username)
    if password_hash is None:
        logger.info("[EdoLogin] '%s' Turon ID bazasida topilmadi.", username)
        return False
    # bcrypt sekin (ataylab) — event loop'ni to'xtatmaslik uchun thread'da
    ok = await asyncio.to_thread(_bcrypt_matches, password, password_hash)
    logger.info("[EdoLogin] '%s': %s", username, "to'g'ri" if ok else "rad etildi")
    return ok

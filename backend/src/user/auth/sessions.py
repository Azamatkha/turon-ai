"""Faol seanslar: qaysi qurilmalardan kirilgan va ularni yopish.

Seans — bitta login (session_id). U Redis'da `refresh:{user}:{sid}` kaliti
bilan yashaydi; shu kalit bor ekan, seans faol. Qurilma ma'lumoti alohida
`session-meta:{user}:{sid}` hash'ida — har bir autentifikatsiyali so'rovda
yangilanadi (dependencies.get_current_user_with_session), shuning uchun
login oqimlarining (parol, EDO, Turon ID, mobil) hech biriga tegilmagan.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
import re

from fastapi import Request
from redis.asyncio import Redis

from src.main.config import config
from src.user.auth.redis_keys import auth_redis_keys

_UA_MAX = 300


def _now_ts() -> str:
    return str(int(datetime.now(UTC).timestamp()))


async def touch_session(
    redis_client: Redis, user_id: str, session_id: str, request: Request | None
) -> None:
    """Seans meta-ma'lumotini yangilaydi: bitta Redis pipeline (arzon).

    `created` faqat birinchi marta yoziladi (HSETNX). TTL — refresh token
    muddati: seans tugasa, meta ham o'zi o'chadi.
    """
    if request is None:
        return
    key = auth_redis_keys.session_meta(user_id, session_id)
    ua = (request.headers.get("user-agent") or "")[:_UA_MAX]
    ip = request.client.host if request.client else ""
    now = _now_ts()
    async with redis_client.pipeline(transaction=False) as pipe:
        pipe.hsetnx(key, "created", now)
        pipe.hset(key, mapping={"ua": ua, "ip": ip, "last_seen": now})
        pipe.expire(key, config.jwt.REFRESH_TOKEN_EXPIRE_MINUTES * 60)
        await pipe.execute()


@dataclass
class SessionInfo:
    session_id: str
    device: str
    user_agent: str
    ip: str
    created_at: datetime | None
    last_seen_at: datetime | None


def describe_device(ua: str) -> str:
    """User-Agent'dan qisqa nom: "Chrome · Windows", "Turon AI ilovasi · Android"."""
    if not ua:
        return ""
    low = ua.lower()
    # Mobil ilova (Flutter/Dart yoki okhttp) — brauzer emas
    if "dart" in low or "okhttp" in low or "turonai" in low or "turon-ai" in low:
        app = "Turon AI app"
    elif "edg/" in low:
        app = "Edge"
    elif "opr/" in low or "opera" in low:
        app = "Opera"
    elif "yabrowser" in low:
        app = "Yandex"
    elif "firefox/" in low:
        app = "Firefox"
    elif "chrome/" in low or "chromium/" in low:
        app = "Chrome"
    elif "safari/" in low:
        app = "Safari"
    else:
        app = ua.split("/")[0].strip()[:30] or "?"

    if "android" in low:
        os_name = "Android"
    elif re.search(r"iphone|ipad|ios", low):
        os_name = "iOS"
    elif "windows" in low:
        os_name = "Windows"
    elif "mac os" in low or "macintosh" in low:
        os_name = "macOS"
    elif "linux" in low:
        os_name = "Linux"
    else:
        os_name = ""
    return f"{app} · {os_name}" if os_name else app


def _ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value), UTC)
    except (TypeError, ValueError):
        return None


async def list_user_sessions(redis_client: Redis, user_id: str) -> list[SessionInfo]:
    """Userning faol seanslari, oxirgi faolligi bo'yicha (yangisi birinchi)."""
    prefix = auth_redis_keys.refresh(user_id, "")
    session_ids: list[str] = []
    cursor = 0
    while True:
        cursor, keys = await redis_client.scan(
            cursor=cursor, match=auth_redis_keys.refresh_pattern(user_id), count=100
        )
        for k in keys:
            key = k.decode() if isinstance(k, bytes) else k
            session_ids.append(key[len(prefix):])
        if cursor == 0:
            break

    sessions: list[SessionInfo] = []
    for sid in dict.fromkeys(session_ids):
        meta = await redis_client.hgetall(auth_redis_keys.session_meta(user_id, sid))
        meta = {
            (k.decode() if isinstance(k, bytes) else k): (
                v.decode() if isinstance(v, bytes) else v
            )
            for k, v in (meta or {}).items()
        }
        ua = meta.get("ua", "")
        sessions.append(
            SessionInfo(
                session_id=sid,
                device=describe_device(ua),
                user_agent=ua,
                ip=meta.get("ip", ""),
                created_at=_ts(meta.get("created")),
                last_seen_at=_ts(meta.get("last_seen")),
            )
        )
    epoch = datetime.fromtimestamp(0, UTC)
    sessions.sort(key=lambda s: s.last_seen_at or epoch, reverse=True)
    return sessions

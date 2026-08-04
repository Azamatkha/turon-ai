"""Real-time signals for new notifications, over Redis pub/sub.

Only a short "there is something new" signal travels through Redis — the
content itself is fetched from the API by the client. That keeps user data out
of the message bus and makes the payload identical for every recipient.

The SSE endpoint in ``routers.py`` subscribes to one channel per user; anything
that inserts notifications calls :func:`publish_new` right *after* the
transaction commits, so the client never queries before the rows are visible.
"""

from collections.abc import Sequence
from uuid import UUID

from redis.asyncio import Redis

from loggers import get_logger
from src.core.redis.core import create_redis_client
from src.main.config import config

logger = get_logger(__name__)

CHANNEL_PREFIX = "notifications:"
NEW_SIGNAL = "new"

# Publishing happens from request handlers and from Celery workers alike, so the
# app-state client is not always available. One lazily created client per
# process is enough — redis-py pools connections internally.
_publisher: Redis | None = None


def channel_for(user_id: UUID) -> str:
    return f"{CHANNEL_PREFIX}{user_id}"


def get_publisher() -> Redis:
    global _publisher
    if _publisher is None:
        _publisher = create_redis_client(config.redis.dsn)
    return _publisher


async def publish_new(user_ids: Sequence[UUID]) -> None:
    """Tell every recipient's open stream that a new notification exists.

    Failures are logged and swallowed: a missed signal only means the client
    falls back to its slower polling interval, which must never break the
    action that produced the notification.
    """
    if not user_ids:
        return
    try:
        redis = get_publisher()
        async with redis.pipeline(transaction=False) as pipe:
            for user_id in user_ids:
                pipe.publish(channel_for(user_id), NEW_SIGNAL)
            await pipe.execute()
    except Exception:
        logger.exception("Bildirishnoma signalini yuborib bo'lmadi")

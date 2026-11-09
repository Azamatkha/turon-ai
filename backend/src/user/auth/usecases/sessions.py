from fastapi import Depends
from redis.asyncio import Redis

from loggers import get_logger
from src.core.errors.exceptions import InstanceNotFoundException
from src.core.redis.dependencies import get_redis_client
from src.user.auth.redis_keys import auth_redis_keys
from src.user.auth.schemas import ActiveSessionView, RevokeSessionsResult
from src.user.auth.sessions import list_user_sessions
from src.user.auth.token_helpers import invalidate_user_session

logger = get_logger(__name__)


class ListActiveSessionsUseCase:
    """Userning faol seanslari; joriy seans belgilanadi va birinchi turadi."""

    def __init__(self, redis_client: Redis) -> None:
        self.redis_client = redis_client

    async def execute(self, user_id: str, current_session_id: str) -> list[ActiveSessionView]:
        sessions = await list_user_sessions(self.redis_client, user_id)
        views = [
            ActiveSessionView(
                session_id=s.session_id,
                device=s.device,
                user_agent=s.user_agent,
                ip=s.ip,
                created_at=s.created_at,
                last_seen_at=s.last_seen_at,
                current=s.session_id == current_session_id,
            )
            for s in sessions
        ]
        views.sort(key=lambda v: not v.current)
        return views


class RevokeSessionUseCase:
    """Bitta seansni yopadi — o'sha qurilma keyingi so'rovda login'ga qaytadi."""

    def __init__(self, redis_client: Redis) -> None:
        self.redis_client = redis_client

    async def execute(self, user_id: str, session_id: str) -> RevokeSessionsResult:
        # Faqat O'Z seansini: kalit user_id bilan quriladi, begona seans
        # topilmaydi
        if not await self.redis_client.exists(auth_redis_keys.refresh(user_id, session_id)):
            raise InstanceNotFoundException("Seans topilmadi")
        await invalidate_user_session(user_id, session_id, self.redis_client)
        logger.info("[Sessions] user %s seansni yopdi: %s", user_id, session_id)
        return RevokeSessionsResult(revoked=1)


class RevokeOtherSessionsUseCase:
    """Joriy seansdan boshqa barcha seanslarni yopadi ("boshqa qurilmalardan chiqish")."""

    def __init__(self, redis_client: Redis) -> None:
        self.redis_client = redis_client

    async def execute(self, user_id: str, current_session_id: str) -> RevokeSessionsResult:
        sessions = await list_user_sessions(self.redis_client, user_id)
        revoked = 0
        for s in sessions:
            if s.session_id == current_session_id:
                continue
            await invalidate_user_session(user_id, s.session_id, self.redis_client)
            revoked += 1
        logger.info("[Sessions] user %s boshqa %d seansni yopdi", user_id, revoked)
        return RevokeSessionsResult(revoked=revoked)


def get_list_active_sessions_use_case(
    redis_client: Redis = Depends(get_redis_client),
) -> ListActiveSessionsUseCase:
    return ListActiveSessionsUseCase(redis_client)


def get_revoke_session_use_case(
    redis_client: Redis = Depends(get_redis_client),
) -> RevokeSessionUseCase:
    return RevokeSessionUseCase(redis_client)


def get_revoke_other_sessions_use_case(
    redis_client: Redis = Depends(get_redis_client),
) -> RevokeOtherSessionsUseCase:
    return RevokeOtherSessionsUseCase(redis_client)

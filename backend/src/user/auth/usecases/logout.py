from uuid import UUID

from fastapi import Depends
from redis.asyncio import Redis

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.redis.dependencies import get_redis_client
from src.core.schemas import SuccessResponse
from src.user.auth.token_helpers import (
    invalidate_all_user_sessions,
    invalidate_user_session,
)

logger = get_logger(__name__)


class LogoutUseCase:
    """Invalidate the current user session or all user sessions."""

    def __init__(
        self,
        redis_client: Redis,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
    ) -> None:
        self.redis_client = redis_client
        self.uow = uow

    async def execute(
        self,
        *,
        user_id: str,
        session_id: str,
        terminate_all_sessions: bool = False,
    ) -> SuccessResponse:
        """
        Invalidate the current user session or all user sessions.

        Flow:
        1. Determine whether current-session or all-session invalidation is required.
        2. Delete the corresponding Redis auth keys.
        3. Return a successful response.

        Returns:
            SuccessResponse with a successful operation flag.
        """
        if terminate_all_sessions:
            await invalidate_all_user_sessions(user_id, self.redis_client)
            logger.debug(
                "[LogoutUser] Invalidated all sessions for user '%s'.", user_id
            )
        else:
            await invalidate_user_session(user_id, session_id, self.redis_client)
            logger.debug(
                "[LogoutUser] Invalidated session '%s' for user '%s'.",
                session_id,
                user_id,
            )

        # So'nggi faollik uchun logout hodisasini yozamiz
        try:
            async with self.uow as uow:
                await uow.login_events.create(
                    uow.session,
                    {"user_id": UUID(user_id), "action": "logout"},
                )
                await uow.commit()
        except Exception:
            logger.exception("[LogoutUser] Failed to record logout event.")

        return SuccessResponse(success=True)


def get_logout_use_case(
    redis_client: Redis = Depends(get_redis_client),
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> LogoutUseCase:
    """Dependency provider for LogoutUseCase."""
    return LogoutUseCase(redis_client=redis_client, uow=uow)

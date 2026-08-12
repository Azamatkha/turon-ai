from uuid import UUID

from fastapi import Depends
from redis.asyncio import Redis

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import InstanceProcessingException
from src.core.redis.dependencies import get_redis_client
from src.core.schemas import SuccessResponse
from src.core.utils.security import hash_password, mask_email, verify_password
from src.user.auth.schemas import UserNewPassword
from src.user.auth.token_helpers import invalidate_all_user_sessions

logger = get_logger(__name__)


class UpdateUserPasswordUseCase:
    """
    Update a user's password and invalidate all their active sessions.

    Inputs:
    - data: UserNewPassword containing the current and the new password.
    - user_id: UUID of the user updating their password.

    Validations:
    - User must exist in the database.
    - `current_password` must match the stored hash. Sababi `UserNewPassword`
      docstring'ida: o'g'irlangan token bilan hisobni egallab olishning oldini
      oladi.

    Workflow:
    1) Load the user and verify the current password.
    2) Hash and update user password in the database.
    3) Flush pending DB changes.
    4) Invalidate all active Redis sessions for the user.
    5) Commit the transaction.

    Side effects:
    - Updates user record in database.
    - Deletes all user session keys from Redis before commit to avoid
      partial-success password changes when Redis is unavailable.

    Errors:
    - InstanceProcessingException: if update fails.

    Returns:
    - SuccessResponse: success=True if updated, False if user not found.
    """

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
        redis_client: Redis,
    ) -> None:
        self.uow = uow
        self.redis_client = redis_client

    async def execute(self, data: UserNewPassword, user_id: UUID) -> SuccessResponse:
        async with self.uow as uow:
            user = await uow.users.get_single(uow.session, id=user_id)
            if not user:
                logger.info("[UpdateUserPassword] User not found.")
                return SuccessResponse(success=False)

            if not await verify_password(data.current_password, user.password_hash):
                # Log'da qaysi foydalanuvchi ekani ko'rinadi (brute-force'ni
                # payqash uchun), lekin urinilgan parolning O'ZI hech qachon
                # yozilmaydi.
                logger.warning(
                    "[UpdateUserPassword] %s uchun joriy parol noto'g'ri.",
                    mask_email(user.email),
                )
                raise InstanceProcessingException("Joriy parol noto'g'ri")

            # Mavjudligi yuqorida tekshirilgani uchun bu yerda qaytadan
            # `if not updated_user` shart emas — bir xil tranzaksiya ichidamiz.
            update_data = {"password_hash": hash_password(data.password)}
            await uow.users.update(uow.session, update_data, id=user_id)

            await uow.flush()
            await invalidate_all_user_sessions(str(user.id), self.redis_client)
            await uow.commit()
            logger.debug(
                "[UpdateUserPassword] %s password updated successfully.",
                mask_email(user.email),
            )
            logger.debug(
                "[UpdateUserPassword] All user %s sessions invalidated.",
                mask_email(user.email),
            )
            return SuccessResponse(success=True)


def get_update_user_password_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
    redis_client: Redis = Depends(get_redis_client),
) -> UpdateUserPasswordUseCase:
    return UpdateUserPasswordUseCase(
        uow=uow,
        redis_client=redis_client,
    )

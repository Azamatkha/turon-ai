import asyncio
from uuid import uuid4

from fastapi import Depends
from redis.asyncio import Redis

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import InstanceProcessingException
from src.core.redis.dependencies import get_redis_client
from src.core.utils.datetime_utils import get_utc_now
from src.core.utils.security import (
    hash_password,
    needs_password_rehash,
    verify_password,
)
from src.user.auth.schemas import LoginTokenModel, LoginUserModel
from src.user.auth.security import create_access_token, create_refresh_token
from src.user.auth.services.mock_p12 import generate_mock_p12
from src.user.models import User

INVALID_CREDENTIALS_MESSAGE = "Incorrect email or password."
INVALID_CREDENTIALS_PASSWORD_HASH = hash_password("dummy-password")
logger = get_logger(__name__)


class LoginUserUseCase:
    """
    Log in a user and return access and refresh tokens.

    Inputs:
    - data: LoginUserModel containing email and password.

    Validations:
    - User must exist.
    - Password must be correct.
    - User must be active (not blocked).

    NOTE on e-mail verification: the template this project started from also
    required ``is_verified`` here. Turon-AI has NO e-mail verification — staff
    accounts are created by an admin, so registration sets ``is_verified=True``
    and this check was removed ON PURPOSE. The docstring used to still list it,
    which made the code look broken; it does not.

    Workflow:
    1) Retrieve user by username.
    2) Verify password (using dummy hash if user not found to prevent timing attacks).
    3) Check if user is active.
    4) Rehash and persist the password if needed.
    5) Generate access and refresh tokens.

    Side effects:
    - Persists password hash updates when rehashing is required.
    - Token creation handles its own caching.

    Errors:
    - InstanceProcessingException: if credentials are invalid, the user is not
      verified, or the user is blocked.

    Returns:
    - LoginTokenModel: tasdiqlangan userga access/refresh tokenlar;
      tasdiqlanmaganga — register'dagidek Face-ID uchun token + p12.
    """

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
        redis_client: Redis,
    ) -> None:
        self.uow = uow
        self.redis_client = redis_client

    async def execute(
        self,
        data: LoginUserModel,
    ) -> LoginTokenModel:
        async with self.uow as uow:
            # Login AYNAN mos kelishi kerak: "turonAI" bilan ro'yxatdan o'tgan
            # odam "turonai" deb kira olmaydi (foydalanuvchi talabi).
            # Bandlik tekshiruvi esa registrsiz — bir-biriga o'xshash ikkita
            # login (turonAI / turonai) umuman yaratilmaydi.
            user = await uow.users.get_single(uow.session, username=data.username)
            if not user:
                logger.debug(
                    "[LoginUser] User '%s' not found.",
                    data.username,
                )
                await verify_password(data.password, INVALID_CREDENTIALS_PASSWORD_HASH)
                raise InstanceProcessingException(INVALID_CREDENTIALS_MESSAGE)

            correct_password = await verify_password(data.password, user.password_hash)
            if not correct_password:
                logger.debug(
                    "[LoginUser] Incorrect password for user '%s'",
                    data.username,
                )
                raise InstanceProcessingException(INVALID_CREDENTIALS_MESSAGE)

            if not user.is_active:
                logger.debug(
                    "[LoginUser] User '%s' is blocked.",
                    data.username,
                )
                raise InstanceProcessingException(INVALID_CREDENTIALS_MESSAGE)

            await self._rehash_password_if_needed(uow, user, data.password)
            # So'nggi faollik + onlayn holat
            user.last_seen_at = get_utc_now()
            await uow.login_events.create(
                uow.session, {"user_id": user.id, "action": "login"}
            )
            session_id = str(uuid4())
            token_data = {"sub": str(user.id)}
            await uow.commit()

        if not user.is_verified:
            return await self._unverified_response(
                token_data, session_id, user.username
            )

        return LoginTokenModel(
            access_token=await create_access_token(
                token_data, redis_client=self.redis_client, session_id=session_id
            ),
            refresh_token=await create_refresh_token(
                token_data,
                redis_client=self.redis_client,
                session_id=session_id,
            ),
            is_verified=True,
        )

    async def _unverified_response(
        self, token_data: dict[str, str], session_id: str, username: str
    ) -> LoginTokenModel:
        """Tasdiqlanmagan user — xuddi register'dagidek Face-ID credential'lari.

        User register qilib, verifikatsiyani tugatmay chiqib ketgan bo'lishi
        mumkin; register'da berilgan token va p12 esa allaqachon eskirgan.
        Login ularni YANGIDAN beradi, shunda verifikatsiyani qayta boshlasa
        bo'ladi. access/refresh esa bo'sh: chat va boshqa API'lar baribir
        unga yopiq (403), refresh ham ishlamaydi.
        """
        # Kalit yaratish CPU'ni band qiladi — event loop'ni to'xtatmaslik uchun
        p12_base64, p12_password = await asyncio.to_thread(
            generate_mock_p12, username
        )
        return LoginTokenModel(
            access_token="",
            refresh_token="",
            is_verified=False,
            token=await create_access_token(
                token_data, redis_client=self.redis_client, session_id=session_id
            ),
            p12_base64=p12_base64,
            p12_password=p12_password,
        )

    async def _rehash_password_if_needed(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
        user: User,
        raw_password: str,
    ) -> None:
        if not needs_password_rehash(user.password_hash):
            return
        await uow.users.update(
            uow.session,
            {"password_hash": hash_password(raw_password)},
            id=user.id,
        )


def get_login_user_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
    redis_client: Redis = Depends(get_redis_client),
) -> LoginUserUseCase:
    return LoginUserUseCase(
        uow=uow,
        redis_client=redis_client,
    )

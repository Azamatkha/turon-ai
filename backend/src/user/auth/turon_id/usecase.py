import secrets
from uuid import uuid4

from fastapi import Depends
from redis.asyncio import Redis

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import InstanceProcessingException
from src.core.redis.dependencies import get_redis_client
from src.core.utils.datetime_utils import get_utc_now
from src.core.utils.security import hash_password
from src.main.config import config
from src.user.auth.schemas import LoginTokenModel
from src.user.auth.security import create_access_token, create_refresh_token
from src.user.auth.turon_id.client import HttpTuronIdGateway, TuronIdGateway
from src.user.auth.turon_id.domain import (
    NAME_MAX_LENGTH,
    USERNAME_MAX_LENGTH,
    TuronIdProfile,
    fallback_username,
    placeholder_email,
    trim,
)
from src.user.models import User

logger = get_logger(__name__)

_UNUSABLE_PASSWORD_BYTES = 32


class TuronIdSignInUseCase:
    """
    Web sign-in through Turon ID: the portal hands the browser a one-time code,
    the backend exchanges it and opens a normal chat session.

    Linking (first match wins): the account already linked to this Turon ID
    user; else an unlinked account with the same phone number; else a new one.
    Turon ID orqali kirish shaxsni TASDIQLAMAYDI: yangi user `is_verified=False`
    bilan yaratiladi va mobil ilovada Face-ID'dan o'tgach tasdiqlanadi
    (`/auth/save`). Tasdiqlanmagan user web'da faqat ogohlantirish sahifasini
    ko'radi — chat API'lari unga 403. Mavjud userning holati o'zgartirilmaydi.
    The chat role follows the Turon ID chat role.

    Errors:
    - UnauthorizedException: the code was refused or the user has no chat role.
    - InstanceProcessingException: Turon ID sign-in is disabled here.
    - InfrastructureException: Turon ID is unreachable.
    """

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
        redis_client: Redis,
        gateway: TuronIdGateway | None,
    ) -> None:
        self.uow = uow
        self.redis_client = redis_client
        self.gateway = gateway

    async def execute(self, code: str) -> LoginTokenModel:
        if self.gateway is None:
            raise InstanceProcessingException("Turon ID sign-in is disabled")
        profile = await self.gateway.sign_in(code)

        async with self.uow as uow:
            user = await self._find_or_create(uow, profile)
            user.turon_id_sub = profile.sub
            user.is_active = True
            user.role = profile.role
            user.last_seen_at = get_utc_now()
            await uow.login_events.create(
                uow.session, {"user_id": user.id, "action": "login"}
            )
            await uow.commit()

        logger.info("[TuronIdSignIn] user %s signed in through Turon ID", user.id)
        session_id = str(uuid4())
        token_data = {"sub": str(user.id)}
        return LoginTokenModel(
            access_token=await create_access_token(
                token_data, redis_client=self.redis_client, session_id=session_id
            ),
            refresh_token=await create_refresh_token(
                token_data, redis_client=self.redis_client, session_id=session_id
            ),
            is_verified=user.is_verified,
        )

    async def _find_or_create(
        self, uow: ApplicationUnitOfWork[RepositoryProtocol], profile: TuronIdProfile
    ) -> User:
        linked = await uow.users.get_single(uow.session, turon_id_sub=profile.sub)
        if linked is not None:
            return linked
        if profile.phone_number:
            by_phone = await uow.users.get_single(
                uow.session, phone_number=profile.phone_number, turon_id_sub=None
            )
            if by_phone is not None:
                logger.info(
                    "[TuronIdSignIn] linked existing user %s by phone", by_phone.id
                )
                return by_phone

        user = await uow.users.create(
            uow.session,
            {
                "first_name": trim(profile.first_name, NAME_MAX_LENGTH),
                "last_name": trim(profile.last_name, NAME_MAX_LENGTH),
                "username": await self._free_username(uow, profile),
                "email": await self._free_email(uow, profile),
                "phone_number": profile.phone_number,
                # Signs in only through Turon ID; nobody knows this password.
                "password_hash": hash_password(
                    secrets.token_urlsafe(_UNUSABLE_PASSWORD_BYTES)
                ),
                "role": profile.role,
                # Face-ID (mobil ilova) dan o'tgandan keyin True bo'ladi
                "is_verified": False,
                "is_active": True,
            },
        )
        await uow.flush()
        logger.info("[TuronIdSignIn] created user %s for Turon ID", user.id)
        return user

    @staticmethod
    async def _free_username(
        uow: ApplicationUnitOfWork[RepositoryProtocol], profile: TuronIdProfile
    ) -> str:
        wanted = trim(profile.username, USERNAME_MAX_LENGTH)
        if wanted and await uow.users.get_single(uow.session, username=wanted) is None:
            return wanted
        return fallback_username(profile.sub)

    @staticmethod
    async def _free_email(
        uow: ApplicationUnitOfWork[RepositoryProtocol], profile: TuronIdProfile
    ) -> str:
        if profile.email and await uow.users.get_single(uow.session, email=profile.email) is None:
            return profile.email
        return placeholder_email(profile.sub)


def get_turon_id_gateway() -> TuronIdGateway | None:
    settings = config.turon_id
    if not settings.TURON_ID_ENABLED:
        return None
    return HttpTuronIdGateway(
        api_url=settings.TURON_ID_API_URL,
        client_id=settings.TURON_ID_CLIENT_ID,
        client_secret=settings.TURON_ID_CLIENT_SECRET,
        public_key=settings.TURON_ID_JWT_PUBLIC_KEY,
        algorithm=settings.TURON_ID_JWT_ALGORITHM,
        timeout_seconds=settings.TURON_ID_TIMEOUT_SECONDS,
    )


def get_turon_id_sign_in_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
    redis_client: Redis = Depends(get_redis_client),
    gateway: TuronIdGateway | None = Depends(get_turon_id_gateway),
) -> TuronIdSignInUseCase:
    return TuronIdSignInUseCase(uow=uow, redis_client=redis_client, gateway=gateway)

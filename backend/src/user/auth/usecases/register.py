from uuid import uuid4

from fastapi import Depends
from redis.asyncio import Redis

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import InstanceAlreadyExistsException
from src.core.redis.dependencies import get_redis_client
from src.core.schemas import TokenModel
from src.core.utils.security import hash_password
from src.user.auth.schemas import DEFAULT_DEPARTMENT, RegisterUserModel
from src.user.auth.security import create_access_token, create_refresh_token
from src.user.constants import build_email

logger = get_logger(__name__)


class RegisterUseCase:
    """Mobil ilova orqali ro'yxatdan o'tish (1-qadam).

    Faqat login + parol olinadi. User `is_verified=False` bilan yoziladi va
    darhol token qaytadi — mobil shu token bilan Face-ID verifikatsiyasiga
    o'tadi (`/users/me/verification/identity` va `/employment`).

    Tasdiqlanmagan user chat va boshqa API'lardan foydalana olmaydi
    (`require_permission` 403 qaytaradi). 3 kun ichida tasdiqlanmasa
    `cleanup_unverified_users` taski uni o'chiradi.
    """

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
        redis_client: Redis,
    ) -> None:
        self.uow = uow
        self.redis_client = redis_client

    async def execute(self, data: RegisterUserModel) -> TokenModel:
        async with self.uow as uow:
            existing = await uow.users.get_single(
                uow.session, username=data.username, is_deleted=False
            )
            if existing:
                raise InstanceAlreadyExistsException("Bu login allaqachon band")

            # Ism/familiya NOT NULL — Face-ID natijasi kelguncha bo'sh turadi
            user_data = {
                "first_name": "",
                "last_name": "",
                "username": data.username,
                "department": DEFAULT_DEPARTMENT,
                "email": build_email(data.username),
                "phone_number": None,
                "password_hash": hash_password(data.password),
                "is_verified": False,
                "is_active": True,
            }
            user = await uow.users.create(session=uow.session, data=user_data)
            await uow.commit()
            logger.info("[Register] '%s' ro'yxatdan o'tdi (tasdiqlanmagan).", data.username)

        session_id = str(uuid4())
        token_data = {"sub": str(user.id)}
        return TokenModel(
            access_token=await create_access_token(
                token_data, redis_client=self.redis_client, session_id=session_id
            ),
            refresh_token=await create_refresh_token(
                token_data, redis_client=self.redis_client, session_id=session_id
            ),
        )


def get_register_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
    redis_client: Redis = Depends(get_redis_client),
) -> RegisterUseCase:
    return RegisterUseCase(uow=uow, redis_client=redis_client)

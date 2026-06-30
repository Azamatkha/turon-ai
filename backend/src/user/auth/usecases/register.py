from fastapi import Depends
from starlette.datastructures import URL

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.utils.security import hash_password
from src.user.auth.schemas import CreateUserModel
from src.user.schemas import UserProfileViewModel

logger = get_logger(__name__)


class RegisterUseCase:
    EMAIL_DOMAIN = "turonbank.uz"

    def __init__(self,uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, data: CreateUserModel) -> UserProfileViewModel:
        async with self.uow as uow:
            parts = data.full_name.strip().split(maxsplit=1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""
            user_data = {
                "first_name": first_name,
                "last_name": last_name,
                "username": data.username,
                "department": data.department,
                "email": f"{data.username}@{self.EMAIL_DOMAIN}",
                "phone_number": None,
                "password_hash": hash_password(data.password),
                "is_verified": True,
                "is_active": True,
            }
            user = await uow.users.create(session=uow.session, data=user_data)
            await uow.commit()
            logger.info("[Register] '%s' ro'yxatdan o'tdi.", data.username)
            return UserProfileViewModel.model_validate(user)

def get_register_use_case(uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),) -> RegisterUseCase:
    return RegisterUseCase(uow=uow)

from fastapi import Depends

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import InstanceAlreadyExistsException
from src.core.utils.security import hash_password
from src.user.constants import build_email, split_full_name
from src.user.schemas import AdminCreateUserModel, UserAdminListItem

logger = get_logger(__name__)


class AdminCreateUserUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, data: AdminCreateUserModel) -> UserAdminListItem:
        async with self.uow as uow:
            existing = await uow.users.get_single(
                uow.session, username=data.username, is_deleted=False
            )
            if existing:
                raise InstanceAlreadyExistsException("Bu login allaqachon band")

            first_name, last_name = split_full_name(data.full_name)

            user_data = {
                "first_name": first_name,
                "last_name": last_name,
                "username": data.username,
                "department": data.department,
                "email": build_email(data.username),
                "phone_number": None,
                "password_hash": hash_password(data.password),
                "role": data.role,
                "is_verified": True,
                "is_active": True,
            }
            user = await uow.users.create(session=uow.session, data=user_data)
            await uow.commit()
            logger.info("[AdminCreateUser] '%s' admin tomonidan yaratildi.", data.username)
            return UserAdminListItem.model_validate(user)


def get_admin_create_user_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> AdminCreateUserUseCase:
    return AdminCreateUserUseCase(uow=uow)
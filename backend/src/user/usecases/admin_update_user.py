from uuid import UUID

from fastapi import Depends

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import (
    InstanceAlreadyExistsException,
    InstanceNotFoundException,
)
from src.core.utils.security import hash_password
from src.user.constants import build_email, split_full_name
from src.user.schemas import AdminUpdateUserModel, UserAdminListItem

logger = get_logger(__name__)


class AdminUpdateUserUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self, user_id: UUID, data: AdminUpdateUserModel
    ) -> UserAdminListItem:
        async with self.uow as uow:
            update_data: dict = {}

            if data.username is not None:
                # Ilgari bu tekshiruv yo'q edi: band login yuborilsa Postgres
                # unique indeksni buzardi va admin tushunarsiz xato ko'rardi.
                # Endi toza 409 + o'zbekcha xabar qaytadi.
                existing = await uow.users.get_single(
                    uow.session, username=data.username, is_deleted=False
                )
                if existing and existing.id != user_id:
                    raise InstanceAlreadyExistsException("Bu login allaqachon band")
                update_data["username"] = data.username
                # Email login'dan hosil qilinadi — ikkalasi birga o'zgaradi
                # (`src/user/constants.py` dagi izohga qarang).
                update_data["email"] = build_email(data.username)
            if data.department is not None:
                update_data["department"] = data.department
            if data.role is not None:
                update_data["role"] = data.role
            if data.password is not None:
                update_data["password_hash"] = hash_password(data.password)
            if data.full_name is not None:
                first_name, last_name = split_full_name(data.full_name)
                update_data["first_name"] = first_name
                update_data["last_name"] = last_name

            if update_data:
                user = await uow.users.update(uow.session, update_data, id=user_id)
            else:
                user = await uow.users.get_single(uow.session, id=user_id)

            if not user:
                raise InstanceNotFoundException("Foydalanuvchi topilmadi")

            await uow.commit()
            return UserAdminListItem.model_validate(user)


def get_admin_update_user_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> AdminUpdateUserUseCase:
    return AdminUpdateUserUseCase(uow=uow)
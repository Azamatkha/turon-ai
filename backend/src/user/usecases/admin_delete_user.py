from uuid import UUID

from fastapi import Depends

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import InstanceNotFoundException
from src.core.schemas import SuccessResponse

logger = get_logger(__name__)


class AdminDeleteUserUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, user_id: UUID) -> SuccessResponse:
        async with self.uow as uow:
            deleted = await uow.users.delete(uow.session, id=user_id)
            if not deleted:
                raise InstanceNotFoundException("Foydalanuvchi topilmadi")
            await uow.commit()
            logger.info("[AdminDeleteUser] '%s' o'chirildi.", deleted.username)
            return SuccessResponse(success=True)


def get_admin_delete_user_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> AdminDeleteUserUseCase:
    return AdminDeleteUserUseCase(uow=uow)
"""Login bo'yicha user verifikatsiyadan (Face-ID) o'tgan-o'tmaganini aytadi.

`GET /v1/users/auth/user/check?username=...` — token talab qilinmaydi.
Faqat bitta bayroq qaytadi (`is_verified`), shaxsiy ma'lumot qaytmaydi.
User topilmasa (yoki o'chirilgan bo'lsa) — 404.
"""

from fastapi import Depends

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import InstanceNotFoundException
from src.user.auth.schemas import UserVerifiedModel

USER_NOT_FOUND_MESSAGE = "Foydalanuvchi topilmadi"
logger = get_logger(__name__)


class CheckUserVerifiedUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, username: str) -> UserVerifiedModel:
        async with self.uow as uow:
            # Registrsiz qidiruv (o'chirilganlarsiz) — "turonAI" va "turonai"
            # bir xil user; bazada ikkalasi bir vaqtda bo'lishi mumkin emas.
            user = await uow.users.get_by_username(uow.session, username)

        if not user:
            logger.debug("[CheckUser] User '%s' not found.", username)
            raise InstanceNotFoundException(USER_NOT_FOUND_MESSAGE)

        return UserVerifiedModel(is_verified=user.is_verified)


def get_check_user_verified_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> CheckUserVerifiedUseCase:
    return CheckUserVerifiedUseCase(uow=uow)

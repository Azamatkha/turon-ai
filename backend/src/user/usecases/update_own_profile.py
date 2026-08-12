from uuid import UUID

from fastapi import Depends

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import (
    InstanceAlreadyExistsException,
    InstanceNotFoundException,
)
from src.user.constants import build_email, split_full_name
from src.user.schemas import UpdateOwnProfileModel, UserProfileViewModel

logger = get_logger(__name__)


class UpdateOwnProfileUseCase:
    """
    Foydalanuvchi o'z profilini (ism, login) yangilaydi.

    Kirish:
    - data: UpdateOwnProfileModel — faqat berilgan maydonlar o'zgaradi.
    - user_id: so'rov yuborayotgan foydalanuvchi (tokendan olinadi, tanadan EMAS —
      aks holda boshqaning profilini o'zgartirib bo'lardi).

    Tekshiruvlar:
    - Yangi login band bo'lmasligi kerak (o'zinikidan boshqa foydalanuvchida).
    - Foydalanuvchi mavjud bo'lishi kerak.

    Nima uchun email ham yangilanadi:
    - `users.email` login'dan hosil qilinadi (`src/user/constants.py` ga qarang).
      Login o'zgarganda emailni eski holida qoldirsak, keyinchalik boshqa xodim
      o'sha eski loginni olganda email bo'yicha unique indeks buzilardi va
      foydalanuvchi tushunarsiz 409 xatosini ko'rardi.

    Nega sessiyalar bekor qilinmaydi:
    - Ism/login o'zgarishi xavfsizlik chegarasini o'zgartirmaydi (rol va huquqlar
      o'sha-o'sha). Token `user_id` ga bog'langan, login'ga emas. Parol
      o'zgarganda esa aksincha — barcha sessiyalar bekor qilinadi.

    Qaytaradi:
    - UserProfileViewModel — yangilangan profil.
    """

    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self, user_id: UUID, data: UpdateOwnProfileModel
    ) -> UserProfileViewModel:
        async with self.uow as uow:
            update_data: dict = {}

            if data.username is not None:
                # `is_deleted=False` — unique indeks ham qisman (partial) va faqat
                # o'chirilmagan qatorlarni qamrab oladi. Buni qo'shmasak, allaqachon
                # o'chirilgan xodimning logini abadiy "band" bo'lib qolardi.
                existing = await uow.users.get_single(
                    uow.session, username=data.username, is_deleted=False
                )
                if existing and existing.id != user_id:
                    raise InstanceAlreadyExistsException("Bu login allaqachon band")
                update_data["username"] = data.username
                update_data["email"] = build_email(data.username)

            if data.full_name is not None:
                first_name, last_name = split_full_name(data.full_name)
                update_data["first_name"] = first_name
                update_data["last_name"] = last_name

            if update_data:
                user = await uow.users.update(uow.session, update_data, id=user_id)
            else:
                # Bo'sh so'rov ({}), ya'ni o'zgartiradigan narsa yo'q — xato emas,
                # shunchaki hozirgi profil qaytariladi (idempotent).
                user = await uow.users.get_single(uow.session, id=user_id)

            if not user:
                raise InstanceNotFoundException("Foydalanuvchi topilmadi")

            await uow.commit()
            logger.info("[UpdateOwnProfile] '%s' profilini yangiladi.", user.username)
            return UserProfileViewModel.model_validate(user)


def get_update_own_profile_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> UpdateOwnProfileUseCase:
    return UpdateOwnProfileUseCase(uow=uow)

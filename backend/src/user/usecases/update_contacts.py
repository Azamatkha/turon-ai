from uuid import UUID

from fastapi import Depends

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import InstanceNotFoundException
from src.user.schemas import UpdateContactsModel, UserProfileViewModel

logger = get_logger(__name__)


class UpdateOwnContactsUseCase:
    """Foydalanuvchi o'z telefon va IP (ichki) raqamini kiritadi yoki o'zgartiradi.

    - `user_id` TOKENDAN olinadi — boshqa odamning raqamini o'zgartirib bo'lmaydi.
    - Faqat yuborilgan maydon o'zgaradi; bo'sh satr raqamni o'chiradi.
    - Raqamlar schema'da allaqachon tekshirilgan va normallashtirilgan
      (`normalize_phone`, `normalize_ip_number`).
    """

    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self, user_id: UUID, data: UpdateContactsModel
    ) -> UserProfileViewModel:
        update_data: dict[str, str | None] = {}
        for field in ("phone_number", "ip_number"):
            value = getattr(data, field)
            if value is not None:
                # Bo'sh satr — raqamni o'chirish (bazada NULL)
                update_data[field] = value or None

        async with self.uow as uow:
            if update_data:
                user = await uow.users.update(uow.session, update_data, id=user_id)
            else:
                # Bo'sh so'rov — xato emas, hozirgi profil qaytadi
                user = await uow.users.get_single(uow.session, id=user_id)
            if not user:
                raise InstanceNotFoundException("Foydalanuvchi topilmadi")
            await uow.commit()
            logger.info("[UpdateContacts] '%s' kontaktlarini yangiladi.", user.username)
            return UserProfileViewModel.model_validate(user)


def get_update_own_contacts_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> UpdateOwnContactsUseCase:
    return UpdateOwnContactsUseCase(uow=uow)

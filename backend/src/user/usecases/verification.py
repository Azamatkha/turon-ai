"""Mobil ilova orqali verifikatsiya: 2 ta alohida save.

Oqim:
1) `/auth/register` — login + parol, user `is_verified=False`.
2) `SaveIdentityUseCase` — Face-ID SDK qaytargan shaxs ma'lumoti (PNFL, FIO, hujjat).
3) `SaveEmploymentUseCase` — xodimlar bazasi PNFL bo'yicha qaytargan
   lavozim/bo'lim/filial. Shu saqlanganda user `is_verified=True` bo'ladi.

Xodimlar bazasi `false` qaytarsa mobil 3-qadamni chaqirmaydi — user
tasdiqlanmagan qoladi (3 kundan keyin `cleanup_unverified_users` o'chiradi).
"""

from uuid import UUID

from fastapi import Depends

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import (
    InstanceAlreadyExistsException,
    InstanceNotFoundException,
    InstanceProcessingException,
)
from src.user.schemas import (
    UserProfileViewModel,
    VerificationEmploymentModel,
    VerificationIdentityModel,
)

logger = get_logger(__name__)

ALREADY_VERIFIED_MESSAGE = "Foydalanuvchi allaqachon tasdiqlangan"


class SaveIdentityUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self, user_id: UUID, data: VerificationIdentityModel
    ) -> UserProfileViewModel:
        async with self.uow as uow:
            user = await uow.users.get_single(uow.session, id=user_id)
            if not user:
                raise InstanceNotFoundException("Foydalanuvchi topilmadi")
            # Tasdiqlangan user FIO/PNFL'ini shu yo'l bilan almashtira olmasin
            if user.is_verified:
                raise InstanceProcessingException(ALREADY_VERIFIED_MESSAGE)

            # Bitta xodim — bitta akkaunt
            owner = await uow.users.get_single(
                uow.session, pnfl=data.pnfl, is_deleted=False
            )
            if owner and owner.id != user_id:
                raise InstanceAlreadyExistsException(
                    "Bu PNFL bilan akkaunt allaqachon mavjud"
                )

            user = await uow.users.update(
                uow.session, data.model_dump(), id=user_id
            )
            await uow.commit()
            logger.info("[Verification] '%s' shaxs ma'lumotlari saqlandi.", user.username)
            return UserProfileViewModel.model_validate(user)


class SaveEmploymentUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self, user_id: UUID, data: VerificationEmploymentModel
    ) -> UserProfileViewModel:
        async with self.uow as uow:
            user = await uow.users.get_single(uow.session, id=user_id)
            if not user:
                raise InstanceNotFoundException("Foydalanuvchi topilmadi")
            if user.is_verified:
                raise InstanceProcessingException(ALREADY_VERIFIED_MESSAGE)
            # Tartib muhim: xodimlar bazasi PNFL bo'yicha tekshiriladi,
            # PNFL esa faqat Face-ID'dan keyin paydo bo'ladi
            if not user.pnfl:
                raise InstanceProcessingException(
                    "Avval Face-ID orqali shaxsni tasdiqlang"
                )

            user = await uow.users.update(
                uow.session,
                {**data.model_dump(), "is_verified": True},
                id=user_id,
            )
            await uow.commit()
            logger.info("[Verification] '%s' tasdiqlandi.", user.username)
            return UserProfileViewModel.model_validate(user)


def get_save_identity_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> SaveIdentityUseCase:
    return SaveIdentityUseCase(uow=uow)


def get_save_employment_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> SaveEmploymentUseCase:
    return SaveEmploymentUseCase(uow=uow)

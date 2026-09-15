"""Mobil ro'yxatdan o'tishning yakuniy qadami — `/auth/save`.

Mobil faqat GSI imzosini (`signature`) yuboradi. Username ham, shaxs
ma'lumoti ham so'rovdan OLINMAYDI — hammasi imzo ichidan:
- user — imzodagi bizning accessToken'dan (`sub`);
- shaxs — imzodagi `body` dan;
- lavozim/bo'lim — xodimlar bazasidan (EDO API, PINFL bo'yicha).
  Xodim bo'lmasa user tasdiqlanmagan qoladi va `{"success": false}` qaytadi.

Qayta yuborishdan himoya: token boshqa userga bog'lab bo'lmaydi (u imzo
ichida), tasdiqlangan user esa ikkinchi marta saqlanmaydi.
"""

from fastapi import Depends
import httpx

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import (
    InstanceAlreadyExistsException,
    InstanceNotFoundException,
    InstanceProcessingException,
)
from src.core.http.dependencies import get_http_client
from src.core.schemas import SuccessResponse
from src.user.auth.schemas import SaveSignatureModel
from src.user.auth.services.employee_check import check_employee
from src.user.auth.services.gsi_signature import (
    decode_signature,
    extract_person,
    user_id_from_token,
)

logger = get_logger(__name__)


class SaveSignatureUseCase:
    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
        http: httpx.AsyncClient,
    ) -> None:
        self.uow = uow
        self.http = http

    async def execute(self, data: SaveSignatureModel) -> SuccessResponse:
        claims = decode_signature(data.signature)
        user_id = user_id_from_token(claims.get("token"))
        person = extract_person(claims.get("body"))

        # Tashqi API tranzaksiyadan OLDIN chaqiriladi — javob kutilayotganda
        # user qatori qulflanib turmasin
        employee = await check_employee(self.http, person.pnfl)
        if employee is None:
            logger.info(
                "[FaceID] User %s xodimlar bazasida topilmadi (requestId=%s).",
                user_id,
                claims.get("requestId"),
            )
            return SuccessResponse(success=False)

        async with self.uow as uow:
            # Qatorni qulflaymiz — bir vaqtdagi ikki so'rov ikkalasi o'tib ketmasin
            user = await uow.users.get_single(uow.session, id=user_id, for_update=True)
            if not user:
                raise InstanceNotFoundException("Foydalanuvchi topilmadi")
            if user.is_verified:
                raise InstanceProcessingException("Foydalanuvchi allaqachon tasdiqlangan")

            # Bitta xodim — bitta akkaunt
            owner = await uow.users.get_single(uow.session, pnfl=person.pnfl)
            if owner and owner.id != user.id:
                raise InstanceAlreadyExistsException(
                    "Bu PNFL bilan akkaunt allaqachon mavjud"
                )

            await uow.users.update(
                uow.session,
                {
                    "pnfl": person.pnfl,
                    "first_name": person.first_name,
                    "last_name": person.last_name,
                    "patronym": person.patronym,
                    "doc_seria": person.doc_seria,
                    "doc_number": person.doc_number,
                    "birth_date": person.birth_date,
                    "position": employee.position,
                    "department": employee.department,
                    "is_verified": True,
                },
                id=user.id,
            )
            await uow.commit()

        logger.info(
            "[FaceID] '%s' tasdiqlandi (requestId=%s, score=%s).",
            user.username,
            claims.get("requestId"),
            claims.get("score"),
        )
        return SuccessResponse(success=True)


def get_save_signature_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
    http: httpx.AsyncClient = Depends(get_http_client),
) -> SaveSignatureUseCase:
    return SaveSignatureUseCase(uow=uow, http=http)

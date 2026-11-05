from uuid import UUID

from fastapi import Depends

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import (
    InstanceAlreadyExistsException,
    InstanceNotFoundException,
    PermissionDeniedException,
)
from src.core.utils.security import hash_password
from src.user.auth.permissions.enum import Permission
from src.user.auth.permissions.role_matrix import ROLE_PERMISSIONS
from src.user.constants import build_email, split_full_name
from src.user.models import User
from src.user.schemas import AdminUpdateUserModel, UserAdminListItem

logger = get_logger(__name__)


class AdminUpdateUserUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self, user_id: UUID, data: AdminUpdateUserModel, current_user: User
    ) -> UserAdminListItem:
        if data.role is not None:
            # Rolni faqat super admin almashtiradi. O'z rolini esa hech kim:
            # oxirgi super admin o'zini pasaytirib, tizimni boshqaruvsiz
            # qoldirmasin.
            if Permission.MANAGE_ROLES not in ROLE_PERMISSIONS.get(current_user.role, set()):
                raise PermissionDeniedException("Rolni faqat super admin o'zgartira oladi")
            if user_id == current_user.id:
                raise PermissionDeniedException("O'z rolingizni o'zgartira olmaysiz")
        async with self.uow as uow:
            update_data: dict = {}

            if data.username is not None:
                # Ilgari bu tekshiruv yo'q edi: band login yuborilsa Postgres
                # unique indeksni buzardi va admin tushunarsiz xato ko'rardi.
                # Endi toza 409 + o'zbekcha xabar qaytadi.
                existing = await uow.users.get_by_username(
                    uow.session, data.username
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
            if data.is_verified is not None:
                # Mobil ilovasiz xodimni admin qo'lda tasdiqlaydi
                update_data["is_verified"] = data.is_verified

            # Verifikatsiya ma'lumotlari (Face-ID'dan o'tolmagan xodim uchun).
            # Bitta PNFL — bitta faol akkaunt (mobil oqimdagi kabi).
            if data.pnfl:
                owner = await uow.users.get_single(
                    uow.session, pnfl=data.pnfl, is_deleted=False
                )
                if owner and owner.id != user_id:
                    raise InstanceAlreadyExistsException(
                        "Bu PNFL bilan akkaunt allaqachon mavjud"
                    )
            for field in (
                "pnfl",
                "patronym",
                "doc_seria",
                "doc_number",
                "position",
                # Kontaktlar — schema'da allaqachon normallashtirilgan
                "phone_number",
                "ip_number",
            ):
                value = getattr(data, field)
                if value is not None:
                    # Bo'sh satr — maydonni tozalash
                    update_data[field] = value.strip() or None
            if data.birth_date is not None:
                update_data["birth_date"] = data.birth_date
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
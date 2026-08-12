from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from src.core.schemas import Base
from src.user.enums import UserRole
from src.user.auth.schemas import CreateUserModel, normalize_department
from src.core.validations import USERNAME_VALIDATOR


class UserProfileViewModel(Base):
    id: UUID
    first_name: str
    last_name: str
    full_name: str
    username: str
    department: str | None = None
    role: UserRole
    email: EmailStr
    phone_number: str | None = None
    is_verified: bool

class UserSummaryViewModel(Base):
    id: UUID
    first_name: str
    last_name: str
    username: str


class UserSummaryWithContactsViewModel(Base):
    id: UUID
    full_name: str
    username: str
    email: EmailStr
    phone_number: str

class UserAdminListItem(Base):
    id: UUID
    username: str
    full_name: str
    department: str | None = None
    role: UserRole
    is_active: bool
    # Oxirgi 5 daqiqada faol bo'lganmi (onlayn/oflayn ko'rsatish uchun).
    # last_seen_at login/so'rov paytida yangilanadi.
    is_online: bool = False


class UpdateOwnProfileModel(Base):
    """Foydalanuvchi O'ZI o'zgartira oladigan maydonlar.

    `role`, `department`, `is_active` bu yerda ATAYLAB yo'q: aks holda oddiy
    xodim o'ziga ADMIN rolini berib qo'ya olardi. Ularni faqat admin
    `AdminUpdateUserModel` orqali o'zgartiradi.

    Parol ham bu yerda emas — u alohida endpointda (`PATCH /me/password`),
    chunki parol o'zgartirish eski parolni tasdiqlashni talab qiladi.

    Har ikkala maydon ixtiyoriy: `None` = "bu maydonga tegma".
    """

    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    username: str | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip().lower()
        if not USERNAME_VALIDATOR.match(value):
            raise ValueError("Login 4-60 belgi: harf, raqam, _ - . bo'lsin")
        return value

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = " ".join(value.split())
        if not value:
            raise ValueError("Ism bo'sh bo'lmasin")
        return value


class AdminCreateUserModel(CreateUserModel):
    role: UserRole = UserRole.USER

class AdminUpdateUserModel(Base):
    username: str | None = None
    full_name: str | None = None
    department: str | None = None
    password: str | None = None
    role: UserRole | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip().lower()
        if not USERNAME_VALIDATOR.match(value):
            raise ValueError("Login 4-60 belgi: harf, raqam, _ - . bo'lsin")
        return value

    @field_validator("department")
    @classmethod
    def validate_department(cls, value: str | None) -> str | None:
        # None = "bu maydonni o'zgartirma" (usecase uni o'tkazib yuboradi),
        # shuning uchun None o'z holicha qoladi. Lekin BO'SH satr yuborilsa —
        # bu "bo'limni o'chir" degani bo'lib qolardi; o'rniga "Boshqa".
        if value is None:
            return None
        return normalize_department(value)
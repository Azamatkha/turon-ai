from datetime import date
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
    # Face-ID va xodimlar bazasidan keladigan ma'lumotlar (tasdiqlangunga qadar bo'sh)
    pnfl: str | None = None
    patronym: str | None = None
    doc_seria: str | None = None
    doc_number: str | None = None
    birth_date: date | None = None
    position: str | None = None
    branch: str | None = None

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
    # Face-ID verifikatsiyasidan o'tganmi (admin qo'lda ham o'zgartira oladi)
    is_verified: bool = True
    position: str | None = None
    branch: str | None = None
    # Admin tahrirlash oynasi uchun (Face-ID'dan o'tolmagan xodimni qo'lda to'ldirish)
    pnfl: str | None = None
    patronym: str | None = None
    doc_seria: str | None = None
    doc_number: str | None = None
    birth_date: date | None = None
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
    # Admin userni qo'lda tasdiqlashi (yoki tasdiqni bekor qilishi) mumkin
    is_verified: bool | None = None
    # Face-ID'dan o'tolmagan xodim ma'lumotlarini admin qo'lda kiritadi.
    # None = maydonga tegma; bo'sh satr = maydonni tozalash (NULL).
    pnfl: str | None = None
    patronym: str | None = Field(default=None, max_length=50)
    doc_seria: str | None = Field(default=None, max_length=10)
    doc_number: str | None = Field(default=None, max_length=20)
    birth_date: date | None = None
    position: str | None = Field(default=None, max_length=150)
    branch: str | None = Field(default=None, max_length=150)

    @field_validator("pnfl")
    @classmethod
    def validate_pnfl(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if value and (len(value) != 14 or not value.isdigit()):
            raise ValueError("PNFL 14 ta raqamdan iborat bo'lishi kerak")
        return value

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


class VerificationIdentityModel(Base):
    """Face-ID (80%+ o'xshashlik) tasdiqlagandan keyin SDK qaytargan ma'lumot.

    Mobil ilova SDK javobini shu ko'rinishda yuboradi.
    """

    pnfl: str
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    patronym: str | None = Field(default=None, max_length=50)
    doc_seria: str | None = Field(default=None, max_length=10)
    doc_number: str | None = Field(default=None, max_length=20)
    birth_date: date

    @field_validator("pnfl")
    @classmethod
    def validate_pnfl(cls, value: str) -> str:
        value = value.strip()
        if len(value) != 14 or not value.isdigit():
            raise ValueError("PNFL 14 ta raqamdan iborat bo'lishi kerak")
        return value

    @field_validator("doc_seria")
    @classmethod
    def validate_doc_seria(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else value


class VerificationEmploymentModel(Base):
    """Xodimlar bazasi PNFL bo'yicha qaytargan ma'lumot (lavozim, bo'lim, filial)."""

    position: str = Field(min_length=1, max_length=150)
    department: str = Field(min_length=1, max_length=100)
    branch: str = Field(min_length=1, max_length=150)
from datetime import date
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from src.core.schemas import Base
from src.user.enums import UserRole
from src.user.auth.schemas import CreateUserModel, normalize_department
from src.core.validations import (
    IP_NUMBER_VALIDATOR,
    USERNAME_VALIDATOR,
    UZ_PHONE_VALIDATOR,
)


PHONE_ERROR = "Telefon raqami +998 va 9 ta raqamdan iborat bo'lsin (masalan +998 99 123 45 67)"
IP_NUMBER_ERROR = "IP raqam 1-4 xonali son bo'lsin (masalan 1036)"


def normalize_phone(value: str | None) -> str | None:
    """Telefon raqamini bazaga yoziladigan ko'rinishga keltiradi.

    None — maydonga tegilmaydi; bo'sh satr — raqam o'chiriladi.
    Foydalanuvchi "+998 99 123-45-67" yoki "(99) 123 45 67" deb yozishi
    mumkin — bo'shliq, defis va qavslar olib tashlanadi. "998..." bilan
    boshlanib "+" tushib qolsa ham qabul qilinadi, 9 ta raqam yozilsa
    +998 o'zi qo'shiladi.
    """
    if value is None:
        return None
    digits = "".join(ch for ch in value if ch.isdigit() or ch == "+")
    if not digits:
        return ""
    if digits.startswith("998") and len(digits) == 12:
        digits = "+" + digits
    elif digits.isdigit() and len(digits) == 9:
        digits = "+998" + digits
    if not UZ_PHONE_VALIDATOR.match(digits):
        raise ValueError(PHONE_ERROR)
    return digits


def normalize_ip_number(value: str | None) -> str | None:
    """IP (ichki) raqamni tekshiradi. None — tegilmaydi, bo'sh satr — o'chiriladi."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return ""
    if not IP_NUMBER_VALIDATOR.match(value):
        raise ValueError(IP_NUMBER_ERROR)
    return value


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
    ip_number: str | None = None
    is_verified: bool
    # Face-ID va xodimlar bazasidan keladigan ma'lumotlar (tasdiqlangunga qadar bo'sh)
    pnfl: str | None = None
    patronym: str | None = None
    doc_seria: str | None = None
    doc_number: str | None = None
    birth_date: date | None = None
    position: str | None = None

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
    phone_number: str | None = None
    ip_number: str | None = None
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
        value = value.strip()
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


class UpdateContactsModel(Base):
    """Foydalanuvchi O'ZI kiritadigan kontaktlar (`PATCH /me/contacts`).

    Ikkalasi ham ixtiyoriy:
      * maydon yuborilmasa (None) — o'zgarmaydi;
      * bo'sh satr ("") — raqam o'chiriladi.
    """

    phone_number: str | None = None
    ip_number: str | None = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        return normalize_phone(value)

    @field_validator("ip_number")
    @classmethod
    def validate_ip_number(cls, value: str | None) -> str | None:
        return normalize_ip_number(value)


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
    # Kontaktlar: None = tegma, bo'sh satr = o'chirish
    phone_number: str | None = None
    ip_number: str | None = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        return normalize_phone(value)

    @field_validator("ip_number")
    @classmethod
    def validate_ip_number(cls, value: str | None) -> str | None:
        return normalize_ip_number(value)

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
        value = value.strip()
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
    """Xodimlar bazasi PNFL bo'yicha qaytargan ma'lumot (lavozim, bo'lim/filial)."""

    position: str = Field(min_length=1, max_length=150)
    department: str = Field(min_length=1, max_length=100)
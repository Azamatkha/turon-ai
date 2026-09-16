from pydantic import ConfigDict, Field, field_validator

from src.core.schemas import (
    Base,
    StrongPasswordValidationMixin,
)
from src.core.validations import USERNAME_VALIDATOR


# Bo'lim MAJBURIY: tanlanmasa shu qiymat qo'yiladi. Frontend ham shuni
# ishlatadi (services/departments.ts -> DEFAULT_DEPARTMENT), lekin kafolat
# shu yerda — API'ga to'g'ridan-to'g'ri murojaat qilinsa ham bo'sh o'tmaydi.
# Bo'limsiz foydalanuvchilar statistikani va bo'lim bo'yicha qidiruvni buzardi.
DEFAULT_DEPARTMENT = "Boshqa"


def normalize_department(value: str | None) -> str:
    return value.strip() if value and value.strip() else DEFAULT_DEPARTMENT


class CreateUserModel(StrongPasswordValidationMixin, Base):
    full_name: str = Field(min_length=2, max_length=100)
    username: str
    department: str = Field(default=DEFAULT_DEPARTMENT, max_length=100)
    password: str

    @field_validator("department", mode="before")
    @classmethod
    def validate_department(cls, value: str | None) -> str:
        return normalize_department(value)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        # Registr SAQLANADI ("turonAI" -> "turonAI"). Bandlik tekshiruvi va
        # login esa registrsiz ishlaydi (`UserRepository.get_by_username`).
        value = value.strip()
        if not USERNAME_VALIDATOR.match(value):
            raise ValueError("Login 4-60 belgi: harf, raqam, _ - . bo'lsin")
        return value


class RegisterUserModel(StrongPasswordValidationMixin, Base):
    """Mobil ilovadan ro'yxatdan o'tish: faqat login + parol.

    Ism, bo'lim va boshqa ma'lumotlar keyin Face-ID va xodimlar bazasidan
    keladi (`/users/me/verification/*`).
    """

    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()
        if not USERNAME_VALIDATOR.match(value):
            raise ValueError("Login 4-60 belgi: harf, raqam, _ - . bo'lsin")
        return value


class RegisterTokenModel(Base):
    """Register javobi: muvaffaqiyat bayrog'i + access token + mock p12.

    Refresh token ataylab berilmaydi — tasdiqlanmagan user baribir refresh
    qila olmaydi; token tugasa (30 daqiqa) mobil qayta login qiladi.

    JSON kalitlari mobil kutgan camelCase'da (`accessToken`, `p12Base64`,
    `p12Password`); Python ichida esa odatdagi snake_case nomlar ishlatiladi.
    """

    model_config = ConfigDict(populate_by_name=True)

    # Bu model faqat muvaffaqiyatli register'da qaytadi — xatolar (login band,
    # validatsiya) exception handler orqali boshqa formatda ketadi.
    success: bool = True
    access_token: str = Field(alias="accessToken")
    # VAQTINCHALIK mock (qara: services/mock_p12.py)
    p12_base64: str = Field(alias="p12Base64")
    p12_password: str = Field(alias="p12Password")


class SaveSignatureModel(Base):
    """`/auth/save` so'rovi: faqat GSI imzolagan Face-ID natijasi (JWT)."""

    signature: str = Field(min_length=1, max_length=100_000)


class LoginUserModel(Base):
    username: str
    password: str


class LogoutRequestModel(Base):
    terminate_all_sessions: bool = False


class UserNewPassword(StrongPasswordValidationMixin, Base):
    """Parolni o'zgartirish so'rovi — faqat yangi parol.

    Joriy parol ataylab SO'RALMAYDI (foydalanuvchi talabi, 2026-09-10).
    Parol o'zgargach barcha sessiyalar bekor qilinadi (update_password.py).
    """

    password: str

from pydantic import ConfigDict, Field, field_validator

from src.core.schemas import (
    Base,
    StrongPasswordValidationMixin,
    TokenModel,
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
        # Registr SAQLANADI ("turonAI" -> "turonAI") va login AYNAN shu
        # ko'rinishda kiritilishi kerak. Faqat BANDLIK tekshiruvi registrsiz
        # (`UserRepository.get_by_username`): "turonai" bilan ikkinchi akkaunt
        # ochilmaydi.
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


class LoginTokenModel(TokenModel):
    """Login javobi — ikki holatdan biri, maydonlar to'plami doim bir xil.

    TASDIQLANGAN user (is_verified=true):
        access_token, refresh_token — to'ldirilgan;
        token, p12Base64, p12Password — bo'sh satr.
    TASDIQLANMAGAN user (is_verified=false) — xuddi register'dagi kabi:
        access_token, refresh_token — bo'sh satr (chat va boshqa API'lar
        baribir yopiq, ular unga kerak emas);
        token — Face-ID SDK'ga beriladigan access token (register'dagi
        accessToken bilan bir xil turdagi), p12Base64 + p12Password — mTLS
        proxy uchun sertifikat. Shu bilan user verifikatsiyani login'dan
        qayta boshlay oladi (register'dagi credential'lar allaqachon eskirgan).

    Kalit nomlari aralash — mobil jamoa bergan formatda: tokenlar snake_case,
    p12 maydonlari register'dagidek camelCase.
    """

    model_config = ConfigDict(populate_by_name=True)

    is_verified: bool
    success: bool = True
    token: str = ""
    p12_base64: str = Field(default="", alias="p12Base64")
    p12_password: str = Field(default="", alias="p12Password")


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

from pydantic import Field, field_validator

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
        value = value.strip().lower()
        if not USERNAME_VALIDATOR.match(value):
            raise ValueError("Login 4-60 belgi: harf, raqam, _ - . bo'lsin")
        return value


class LoginUserModel(Base):
    username: str
    password: str


class LogoutRequestModel(Base):
    terminate_all_sessions: bool = False


class UserNewPassword(StrongPasswordValidationMixin, Base):
    """Parolni o'zgartirish so'rovi.

    `current_password` MAJBURIY. Sababi: access token o'g'irlansa (masalan
    xodim kompyuterini qulflamay ketsa yoki XSS orqali), token egasi eski
    parolni bilmasa ham yangi parol qo'yib, HAQIQIY egasini o'z hisobidan
    butunlay chiqarib yubora olardi. Joriy parolni so'rash bu yo'lni yopadi.

    `StrongPasswordValidationMixin` faqat `password` maydonini tekshiradi
    (`check_fields=False` bilan nom bo'yicha), `current_password` esa xohlagan
    ko'rinishda bo'lishi mumkin — u eskisi, uni qayta validatsiya qilish
    noto'g'ri bo'lardi (talablar o'zgargan bo'lishi mumkin).
    """

    current_password: str
    password: str

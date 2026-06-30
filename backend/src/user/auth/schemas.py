from pydantic import Field, field_validator

from src.core.schemas import (
    Base,
    StrongPasswordValidationMixin,
)
from src.core.validations import USERNAME_VALIDATOR


class CreateUserModel(StrongPasswordValidationMixin, Base):
    full_name: str = Field(min_length=2, max_length=100)
    username: str
    department: str | None = Field(default=None, max_length=100)
    password: str

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
    password: str

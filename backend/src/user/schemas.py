from uuid import UUID

from pydantic import EmailStr,field_validator

from src.core.schemas import Base
from src.user.enums import UserRole
from src.user.auth.schemas import CreateUserModel
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
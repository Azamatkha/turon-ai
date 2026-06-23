from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.user.enums import UserRole


class AdminUserView(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID
    username: str
    full_name: str
    department: str | None = None
    role: str
    is_active: bool


class AdminUserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=60)
    full_name: str = Field(min_length=1, max_length=100)
    department: str | None = Field(default=None, max_length=100)
    password: str = Field(min_length=4, max_length=128)
    role: UserRole = UserRole.USER


class RoleUpdate(BaseModel):
    role: UserRole


class AdminUserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=60)
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    department: str | None = Field(default=None, max_length=100)
    password: str | None = Field(default=None, min_length=4, max_length=128)


class UsersListResponse(BaseModel):
    total: int
    users: list[AdminUserView]

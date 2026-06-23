from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    # Frontend "login" maydonini yuboradi (username yoki email bo'lishi mumkin)
    login: str
    password: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=60)
    full_name: str = Field(min_length=1, max_length=100)
    department: str | None = Field(default=None, max_length=100)
    password: str = Field(min_length=4, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str = "user"


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID
    username: str
    email: str
    full_name: str
    department: str | None = None
    role: str

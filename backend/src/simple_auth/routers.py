"""Oddiy auth endpointlari: register / login / logout / me (frontend uchun)."""
from typing import Annotated

from fastapi import APIRouter, Depends

from src.core.errors.exceptions import UnauthorizedException
from src.core.schemas import SuccessResponse
from src.simple_auth.dependencies import get_current_user, get_simple_auth_service
from src.simple_auth.schemas import (
    LoginRequest,
    MeResponse,
    RegisterRequest,
    TokenResponse,
)
from src.simple_auth.security import create_access_token
from src.simple_auth.service import SimpleAuthService
from src.user.models import User

router = APIRouter()


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        role=str(user.role.value if hasattr(user.role, "value") else user.role),
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    service: Annotated[SimpleAuthService, Depends(get_simple_auth_service)],
) -> TokenResponse:
    user = await service.register(
        username=payload.username,
        full_name=payload.full_name,
        password=payload.password,
        department=payload.department,
    )
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    service: Annotated[SimpleAuthService, Depends(get_simple_auth_service)],
) -> TokenResponse:
    user = await service.authenticate(payload.login, payload.password)
    if user is None:
        raise UnauthorizedException("Login yoki parol noto'g'ri")
    return _token_response(user)


@router.post("/logout", response_model=SuccessResponse)
async def logout(_: Annotated[User, Depends(get_current_user)]) -> SuccessResponse:
    # JWT stateless — token mijoz tomonida o'chiriladi.
    return SuccessResponse(success=True)


@router.get("/me", response_model=MeResponse)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> MeResponse:
    return MeResponse.model_validate(current_user)

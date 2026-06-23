from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import get_session
from src.core.errors.exceptions import AccessForbiddenException, UnauthorizedException
from src.simple_auth.security import decode_access_token
from src.simple_auth.service import SimpleAuthService
from src.user.enums import UserRole
from src.user.models import User

_bearer = HTTPBearer(auto_error=True)


def get_simple_auth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SimpleAuthService:
    return SimpleAuthService(session)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    service: Annotated[SimpleAuthService, Depends(get_simple_auth_service)],
) -> User:
    user_id = decode_access_token(credentials.credentials)
    user = await service.get_by_id(user_id)
    if user is None:
        raise UnauthorizedException("Foydalanuvchi topilmadi")
    return user


async def get_current_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Faqat ADMIN rolidagi foydalanuvchiga ruxsat beradi (aks holda 403)."""
    if user.role != UserRole.ADMIN:
        raise AccessForbiddenException("Faqat admin uchun")
    return user

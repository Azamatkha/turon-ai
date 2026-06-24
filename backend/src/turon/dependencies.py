"""
FastAPI dependencies: extract the current account from the Bearer token,
and a guard that only lets admins through.
"""

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import get_session
from src.turon.models import Account, AccountRole
from src.turon.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_account(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    session: AsyncSession = Depends(get_session),
) -> Account:
    """Decode the JWT, load the account, and ensure it is still active."""
    try:
        payload = decode_access_token(credentials.credentials)
        account_id = UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token yaroqsiz yoki muddati o'tgan.",
        )

    account = await session.get(Account, account_id)
    if account is None or not account.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Hisob topilmadi yoki faol emas.",
        )
    return account


async def require_admin(
    account: Annotated[Account, Depends(get_current_account)],
) -> Account:
    """Allow the request only if the current account is an admin."""
    if account.role != AccountRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu amal faqat administrator uchun.",
        )
    return account

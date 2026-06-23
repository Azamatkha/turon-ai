"""JWT access token: yaratish va tekshirish.

Sozlamalar (maxfiy kalit, algoritm, muddat) env'dan keladigan config.jwt'dan
olinadi — hech narsa qattiq yozilmagan.
"""
from datetime import datetime, timedelta, timezone

import jwt

from src.core.errors.exceptions import UnauthorizedException
from src.main.config import config


def create_access_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=config.jwt.ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }
    return jwt.encode(
        payload, config.jwt.JWT_USER_SECRET_KEY, algorithm=config.jwt.ALGORITHM
    )


def decode_access_token(token: str) -> str:
    """Tokenni tekshirib, ichidagi foydalanuvchi id'sini (sub) qaytaradi."""
    try:
        payload = jwt.decode(
            token, config.jwt.JWT_USER_SECRET_KEY, algorithms=[config.jwt.ALGORITHM]
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedException("Token noto'g'ri yoki muddati o'tgan") from exc

    subject = payload.get("sub")
    if not subject:
        raise UnauthorizedException("Token tarkibi noto'g'ri")
    return str(subject)

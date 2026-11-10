import hmac
from typing import Annotated

from fastapi import Header

from src.core.errors.exceptions import PermissionDeniedException, UnauthorizedException
from src.main.config import config

SYNC_DISABLED = "Telegram bot sinxronizatsiyasi o'chiq"
BAD_BOT_KEY = "Bot kaliti noto'g'ri"


async def verify_bot_key(
    x_bot_key: Annotated[str | None, Header(alias="X-Bot-Key")] = None,
) -> None:
    """Bot (mashina) so'rovi: `X-Bot-Key` header .env dagi kalitga teng bo'lishi kerak.

    Kalit .env da berilmagan bo'lsa endpoint umuman yopiq.
    """
    expected = config.telegram_bot.TELEGRAM_BOT_API_KEY
    if not expected:
        raise PermissionDeniedException(SYNC_DISABLED)
    if not x_bot_key or not hmac.compare_digest(x_bot_key.encode(), expected.encode()):
        raise UnauthorizedException(BAD_BOT_KEY)

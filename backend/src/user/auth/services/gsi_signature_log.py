"""Kelgan GSI `signature` ni `face_id_signature_logs` jadvaliga yozish.

Asosiy so'rovdan ALOHIDA sessiya va tranzaksiyada yoziladi: `/auth/save`
xato bilan tugasa ham (rollback bo'lsa ham) yozuv saqlanib qoladi.
Yozishda xato bo'lsa — faqat logga tushadi, ro'yxatdan o'tishni buzmaydi.
"""

import json
from typing import Any
from uuid import UUID

from loggers import get_logger
from src.core.database.session import async_session
from src.user.models import FaceIdSignatureLog

logger = get_logger(__name__)


def _readable_claims(claims: dict[str, Any] | None) -> dict[str, Any] | None:
    """`body` GSI'dan JSON SATR bo'lib keladi — o'qish oson bo'lsin deb ochamiz."""
    if claims is None:
        return None
    body = claims.get("body")
    if isinstance(body, str):
        try:
            return {**claims, "body": json.loads(body)}
        except json.JSONDecodeError:
            pass
    return claims


async def store_signature_log(
    *,
    signature: str,
    claims: dict[str, Any] | None,
    user_id: UUID | None,
    result: str,
) -> None:
    try:
        request_id = claims.get("requestId") if claims else None
        async with async_session() as session:
            session.add(
                FaceIdSignatureLog(
                    user_id=user_id,
                    request_id=str(request_id)[:100] if request_id else None,
                    signature=signature,
                    claims=_readable_claims(claims),
                    result=result[:255],
                )
            )
            await session.commit()
    except Exception:
        logger.exception("[FaceID] signature log yozilmadi.")

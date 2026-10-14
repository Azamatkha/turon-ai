"""Face-ID accessToken'ini GSI'ga yuborishdan OLDIN tekshirish (mTLS proxy uchun).

Proxy SDK so'rovini GSI'ga uzatishdan oldin shu yerdan so'raydi. Tekshiruvlar
(GSI talabi, hujjat 5.6 va 7.1):
- token bor;
- imzo bizning kalit (`JWT_USER_SECRET_KEY`) bilan yaroqli;
- `exp` o'tmagan;
- `verificationId` tokenda va Redis'da bor, tokendagi user'ga tegishli.

Birortasi o'tmasa — 401: proxy so'rovni GSI'ga yubormaydi, webhook chaqirilmaydi.
"""

from fastapi import Depends
from redis.asyncio import Redis

from loggers import get_logger
from src.core.errors.exceptions import UnauthorizedException
from src.core.redis.dependencies import get_redis_client
from src.core.schemas import SuccessResponse
from src.user.auth.services.gsi_signature import FaceIdRejected, user_id_from_token

logger = get_logger(__name__)

INVALID_TOKEN_MESSAGE = "Face-ID token yaroqsiz"


class CheckFaceTokenUseCase:
    def __init__(self, redis_client: Redis) -> None:
        self.redis_client = redis_client

    async def execute(self, token: str) -> SuccessResponse:
        try:
            user_id = await user_id_from_token(
                token, self.redis_client, verify_exp=True
            )
        except FaceIdRejected as exc:
            # Aniq sabab FaceIdRejected ichida logga yozilgan; tashqariga — umumiy
            raise UnauthorizedException(INVALID_TOKEN_MESSAGE) from exc

        logger.info("[FaceID] Token tekshiruvdan o'tdi (user=%s).", user_id)
        return SuccessResponse(success=True)


def get_check_face_token_use_case(
    redis_client: Redis = Depends(get_redis_client),
) -> CheckFaceTokenUseCase:
    return CheckFaceTokenUseCase(redis_client=redis_client)

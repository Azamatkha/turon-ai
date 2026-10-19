"""Face-ID accessToken'ini GSI'ga yuborishdan OLDIN tekshirish (mTLS proxy uchun).

Proxy SDK so'rovini GSI'ga uzatishdan oldin shu yerdan so'raydi. Tekshiruvlar
(GSI talabi, hujjat 5.6 va 7.1):
- token bor;
- imzo bizning kalit (`JWT_USER_SECRET_KEY`) bilan yaroqli;
- `exp` o'tmagan;
- `verificationId` tokenda va Redis'da bor, tokendagi user'ga tegishli.

Birortasi o'tmasa — 401: proxy so'rovni GSI'ga yubormaydi, webhook chaqirilmaydi.

Token yaroqli bo'lsa — rate limit (hujjat 12, 16.3): bitta user
`FACE_ID_RATE_LIMIT_SECONDS` (15 s) ichida faqat 1 marta o'tadi, qolgani 429.
Cheklov user_id bo'yicha: bitta IP ortidagi turli userlar bir-birini
bloklamaydi, qayta login qilib yangi token olish ham uni aylanib o'tmaydi.
"""

from fastapi import Depends
from redis.asyncio import Redis

from loggers import get_logger
from src.core.errors.exceptions import (
    TooManyRequestsException,
    UnauthorizedException,
)
from src.core.redis.dependencies import get_redis_client
from src.core.schemas import SuccessResponse
from src.main.config import config
from src.user.auth.redis_keys import auth_redis_keys
from src.user.auth.services.gsi_signature import FaceIdRejected, user_id_from_token

logger = get_logger(__name__)

INVALID_TOKEN_MESSAGE = "Face-ID token yaroqsiz"
RATE_LIMIT_MESSAGE = "Face-ID so'rovi juda tez-tez yuborilmoqda"


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

        # SET NX EX — atomar: bir vaqtda kelgan ikki so'rovdan faqat bittasi o'tadi
        rate_key = auth_redis_keys.face_id_rate_limit(str(user_id))
        acquired = await self.redis_client.set(
            rate_key, "1", nx=True, ex=config.jwt.FACE_ID_RATE_LIMIT_SECONDS
        )
        if not acquired:
            retry_after = await self.redis_client.ttl(rate_key)
            logger.info("[FaceID] Rate limit (user=%s, %ss).", user_id, retry_after)
            raise TooManyRequestsException(
                message=RATE_LIMIT_MESSAGE, retry_after=max(retry_after, 1)
            )

        logger.info("[FaceID] Token tekshiruvdan o'tdi (user=%s).", user_id)
        return SuccessResponse(success=True)


def get_check_face_token_use_case(
    redis_client: Redis = Depends(get_redis_client),
) -> CheckFaceTokenUseCase:
    return CheckFaceTokenUseCase(redis_client=redis_client)

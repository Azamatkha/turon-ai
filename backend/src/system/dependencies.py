import httpx
from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import get_session
from src.core.http.dependencies import get_http_client
from src.core.redis.dependencies import get_redis_client
from src.system.readiness import ReadinessService
from src.system.services import HealthService


async def get_health_service(
    redis_client: Redis = Depends(get_redis_client),
) -> HealthService:
    return HealthService(redis_client=redis_client)


async def get_readiness_service(
    session: AsyncSession = Depends(get_session),
    redis_client: Redis = Depends(get_redis_client),
    http: httpx.AsyncClient = Depends(get_http_client),
) -> ReadinessService:
    return ReadinessService(session=session, redis=redis_client, http=http)

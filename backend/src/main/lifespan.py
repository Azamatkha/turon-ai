from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from src.core.http.lifecycle import on_http_shutdown, on_http_startup
from src.core.redis.cache.lifecycle import (
    on_redis_cache_shutdown,
    on_redis_cache_startup,
)
from src.core.redis.lifecycle import on_redis_shutdown, on_redis_startup
from src.main.config import config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    await on_redis_startup(app, config.redis.dsn)

    await on_redis_cache_startup()
    await on_http_startup(app)

    yield

    await on_redis_cache_shutdown()
    await on_redis_shutdown(app)
    await on_http_shutdown(app)

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI

from src.core.http.lifecycle import on_http_shutdown, on_http_startup
from src.core.redis.cache.lifecycle import (
    on_redis_cache_shutdown,
    on_redis_cache_startup,
)
from src.core.redis.lifecycle import on_redis_shutdown, on_redis_startup
from src.core.vectorstore.dependencies import get_vector_store
from src.main.config import config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    # Foydalanuvchi yuklagan fayllar papkasi (murojaat skrinshotlari)
    Path(config.app.MEDIA_ROOT).mkdir(parents=True, exist_ok=True)

    await on_redis_startup(app, config.redis.dsn)

    await on_redis_cache_startup()
    await on_http_startup(app)

    # Qdrant payload indekslari — fonda (Qdrant sekin/o'chiq bo'lsa ham ilova
    # ishga tushishini to'xtatmaydi; xato ichkarida logga yoziladi).
    index_task: asyncio.Task[None] | None = None
    if not config.app.TESTING:
        index_task = asyncio.create_task(get_vector_store().ensure_payload_indexes())

    yield

    if index_task is not None and not index_task.done():
        index_task.cancel()

    await on_redis_cache_shutdown()
    await on_redis_shutdown(app)
    await on_http_shutdown(app)

"""Sinov stendi fon vazifalari (admin tugmasi bilan ishga tushadi).

O'lchov uzoq: har savol — botning to'liq javobi (tekshiruvchi bilan) + hakam.
Shuning uchun umumiy 30 daqiqalik limit o'rniga o'z limiti bor.
"""

from uuid import UUID

import httpx

from celery_tasks.main import celery_app, local_async_session  # noqa: F401
from celery_tasks.types import typed_shared_task
from loggers import get_logger
from src.core.ai.embeddings import OllamaEmbedder
from src.core.ai.factory import AIClientFactory
from src.core.redis.core import create_redis_client
from src.core.utils.coroutine_runner import execute_coroutine_sync
from src.core.vectorstore.qdrant_store import QdrantStore
from src.evaluation.usecases import (
    EVAL_GENERATING_KEY,
    EVAL_GENERATING_TTL,
    ExecuteEvalRunUseCase,
    GenerateEvalCasesUseCase,
)
from src.main.config import config

logger = get_logger(__name__)

GENERATE_TIME_LIMIT = EVAL_GENERATING_TTL
RUN_TIME_LIMIT = 10 * 3600


@typed_shared_task(name="generate_eval_cases", time_limit=GENERATE_TIME_LIMIT)
def generate_eval_cases(max_docs: int = 30) -> str:
    return execute_coroutine_sync(coroutine=lambda: _generate(max_docs))


async def _generate(max_docs: int) -> str:
    redis = create_redis_client(config.redis.dsn)
    try:
        if not await redis.set(EVAL_GENERATING_KEY, "1", nx=True, ex=EVAL_GENERATING_TTL):
            return "already running"
        # Savol tuzish uzoq — timeout uzun HTTP klient
        async with httpx.AsyncClient(timeout=None) as http:
            ai = AIClientFactory.create(config.ai.AI_PROVIDER, http)
            count = await GenerateEvalCasesUseCase(
                local_async_session, QdrantStore(), ai
            ).execute(max_docs)
        return f"cases={count}"
    finally:
        await redis.delete(EVAL_GENERATING_KEY)
        await redis.aclose()


@typed_shared_task(name="run_eval", time_limit=RUN_TIME_LIMIT)
def run_eval(run_id: str) -> str:
    return execute_coroutine_sync(coroutine=lambda: _run(UUID(run_id)))


async def _run(run_id: UUID) -> str:
    # Javob yo'lini import qilish og'ir — faqat vazifa ichida
    from src.knowledge.usecases import AnswerQuestionUseCase

    store = QdrantStore()
    async with httpx.AsyncClient(timeout=None) as http:
        ai = AIClientFactory.create(config.ai.AI_PROVIDER, http)
        embedder = OllamaEmbedder(http=http)
        return await ExecuteEvalRunUseCase(
            local_async_session,
            store,
            lambda: AnswerQuestionUseCase(embedder=embedder, store=store, ai_client=ai),
            ai,
        ).execute(run_id)

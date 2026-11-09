"""Tizim komponentlarining holati (readiness).

Har bir komponent parallel va qisqa timeout bilan tekshiriladi — bitta
osilib qolgan xizmat butun tekshiruvni sekinlashtirmasin. Tekshiruvlar
ARZON: Ollama'da generatsiya chaqirilmaydi (/api/ps — faqat yuklangan
modellar ro'yxati), Celery'ga bitta ping.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import time

import httpx
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from loggers import get_logger
from src.main.config import config

logger = get_logger(__name__)

CHECK_TIMEOUT_S = 3.0

# Ishlamasa chat umuman javob bera olmaydigan komponentlar. Qolganlari
# (RabbitMQ, Celery) fon vazifalari uchun — ular yiqilsa ham chat ishlaydi,
# shuning uchun /health/ready ularni "degraded" deb ko'rsatadi, 503 emas.
CRITICAL = ("postgres", "redis", "qdrant", "ollama")


@dataclass
class ComponentStatus:
    name: str
    ok: bool
    latency_ms: int
    critical: bool
    detail: str = ""


async def _timed(
    name: str, check: Callable[[], Awaitable[str]]
) -> ComponentStatus:
    start = time.perf_counter()
    try:
        detail = await asyncio.wait_for(check(), timeout=CHECK_TIMEOUT_S)
        ok = True
    except TimeoutError:
        ok, detail = False, "timeout"
    except Exception as exc:  # noqa: BLE001 - har qanday xato = komponent ishlamayapti
        ok, detail = False, type(exc).__name__
        logger.warning("Readiness: %s ishlamayapti: %r", name, exc)
    return ComponentStatus(
        name=name,
        ok=ok,
        latency_ms=int((time.perf_counter() - start) * 1000),
        critical=name in CRITICAL,
        detail=detail,
    )


class ReadinessService:
    def __init__(
        self, session: AsyncSession, redis: Redis, http: httpx.AsyncClient
    ) -> None:
        self.session = session
        self.redis = redis
        # Ollama boshqa serverda — ilovaning umumiy klienti (u bilan chat ishlaydi)
        self.http = http

    async def check_all(self) -> list[ComponentStatus]:
        return list(
            await asyncio.gather(
                _timed("postgres", self._postgres),
                _timed("redis", self._redis),
                _timed("qdrant", self._qdrant),
                _timed("ollama", self._ollama),
                _timed("rabbitmq", self._rabbitmq),
                _timed("celery", self._celery),
            )
        )

    async def _postgres(self) -> str:
        await self.session.execute(text("SELECT 1"))
        return ""

    async def _redis(self) -> str:
        if not await self.redis.ping():
            raise RuntimeError("ping false")
        return ""

    async def _qdrant(self) -> str:
        base = f"http://{config.qdrant.QDRANT_HOST}:{config.qdrant.QDRANT_PORT}"
        collection = config.qdrant.QDRANT_COLLECTION
        # trust_env=False: korporativ proksi ichki `qdrant` xostiga aralashmasin
        async with httpx.AsyncClient(base_url=base, trust_env=False) as client:
            res = await client.get(f"/collections/{collection}")
            res.raise_for_status()
            points = (res.json().get("result") or {}).get("points_count")
        return f"{points} points" if points is not None else ""

    async def _ollama(self) -> str:
        base = config.ai.OLLAMA_BASE_URL.rstrip("/")
        res = await self.http.get(f"{base}/api/ps", timeout=CHECK_TIMEOUT_S)
        res.raise_for_status()
        models = [m.get("name") or m.get("model") for m in res.json().get("models") or []]
        want = config.ai.OLLAMA_MODEL
        # Server ishlayapti, lekin model xotirada emas — birinchi savol sekin
        # bo'ladi (model yuklanadi). Bu xato emas, faqat ma'lumot.
        return f"{want}: {'loaded' if want in models else 'not loaded'}"

    async def _rabbitmq(self) -> str:
        reader, writer = await asyncio.open_connection(
            config.rabbitmq.RABBITMQ_HOST, config.rabbitmq.RABBITMQ_PORT
        )
        writer.close()
        await writer.wait_closed()
        return ""

    async def _celery(self) -> str:
        # Import shu yerda: veb-jarayon Celery ilovasini faqat kerak bo'lganda yuklasin
        from celery_tasks.main import celery_app

        replies = await asyncio.to_thread(
            celery_app.control.ping, timeout=CHECK_TIMEOUT_S - 1
        )
        if not replies:
            raise RuntimeError("no workers")
        return f"{len(replies)} worker"


def overall_status(components: list[ComponentStatus]) -> str:
    """"ok" | "degraded" (ikkinchi darajali yiqilgan) | "down" (muhim yiqilgan)."""
    if any(not c.ok and c.critical for c in components):
        return "down"
    if any(not c.ok for c in components):
        return "degraded"
    return "ok"

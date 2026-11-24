"""PDF yuklash — FONDA. Holati Redis'da.

Muammo (2026-11-23): 9 sahifali skanni model 77 soniyada o'qidi va bazaga
yozdi (backend 200 qaytardi), lekin brauzer "PDF yuklashda xatolik" ko'rdi.
Bizning nginx 300 soniya kutadi — so'rovni ORALIQDAGI proxy (bank tarmog'i,
odatda 60 soniya chegarasi) uzgan. Proxy bizning nazoratimizda emas, shuning
uchun so'rov uzoq ushlab turilmaydi: fayl qabul qilinadi, ish fonda
bajariladi, admin sahifasi holatni so'rab turadi ("5/9 sahifa").

Nega Celery emas: asosiy worker `--pool=solo` (bitta vazifa) — uzun PDF kurs,
email va zaxira vazifalarini to'sardi; fayl baytlarini broker orqali
uzatish ham kerak bo'lardi. Ish ilova jarayonida bajariladi, holat esa
Redis'da — 4 ta uvicorn worker'idan qaysi biri so'rasa ham ko'radi.
Ilova qayta ishga tushsa (deploy) tugallanmagan ish "yiqildi" bo'lib
ko'rinadi (jim qolish chegarasi) — admin faylni qayta yuklaydi.
"""

import asyncio
from collections.abc import Awaitable, Callable
import json
from typing import Any
from uuid import uuid4

from fastapi import Depends
from redis.asyncio import Redis

from loggers import get_logger
from src.core.ai.dependencies import get_ai_client
from src.core.ai.embeddings import OllamaEmbedder, get_embedder
from src.core.ai.interfaces import BaseAIClient
from src.core.database.session import async_session
from src.core.database.uow import get_uow
from src.core.errors.exceptions import (
    InstanceNotFoundException,
    InstanceProcessingException,
)
from src.core.redis.dependencies import get_redis_client
from src.core.utils.datetime_utils import get_utc_now
from src.core.vectorstore.dependencies import get_vector_store
from src.core.vectorstore.qdrant_store import QdrantStore
from src.knowledge.ingest_usecases import UploadPdfUseCase
from src.knowledge.schemas import PdfJobView, PdfUploadResult
from src.notifications.enums import NotificationType
from src.notifications.usecases import BroadcastNotificationUseCase
from src.user.enums import UserRole

logger = get_logger(__name__)

JOB_KEY = "pdf-job:{}"
# Oxirgi ishlar ro'yxati (sorted set: id -> yaratilgan vaqt)
JOBS_INDEX = "pdf-jobs"
JOB_TTL_SECONDS = 24 * 3600
RECENT_LIMIT = 10
# Shuncha vaqt holati yangilanmagan "faol" ish — jarayon o'lgan (deploy).
# Bitta sahifa 3 daqiqagacha o'qilishi mumkin (VISION_PAGE_TIMEOUT), zaxira bilan.
STALE_AFTER_SECONDS = 10 * 60
ACTIVE_STATUSES = ("queued", "running")

# Bir jarayonda bir vaqtda bitta PDF: GPU jonli savollar bilan bo'lishiladi,
# bir nechta skan birdan yuborilsa chat javoblari sekinlashardi.
_SEMAPHORE = asyncio.Semaphore(1)
# Fon vazifalari GC tomonidan yig'ib olinmasligi uchun kuchli havola
_tasks: set[asyncio.Task[None]] = set()

STALE_ERROR = "Ish to'xtab qoldi (server qayta ishga tushgan bo'lishi mumkin). Faylni qayta yuklang."
FAILED_ERROR = "PDF'ni qayta ishlashda kutilmagan xato"
JOB_NOT_FOUND = "Yuklash ishi topilmadi (muddati o'tgan bo'lishi mumkin)"


class PdfJobStore:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def create(self, filename: str, title: str) -> PdfJobView:
        now = get_utc_now()
        job = PdfJobView(
            id=uuid4().hex,
            status="queued",
            filename=filename,
            title=title,
            created_at=now,
            updated_at=now,
        )
        await self._save(job)
        await self.redis.zadd(JOBS_INDEX, {job.id: now.timestamp()})
        return job

    async def _save(self, job: PdfJobView) -> None:
        await self.redis.set(
            JOB_KEY.format(job.id), job.model_dump_json(), ex=JOB_TTL_SECONDS
        )

    async def update(self, job_id: str, **fields: Any) -> PdfJobView | None:
        job = await self._load(job_id)
        if job is None:
            return None
        job = job.model_copy(update={**fields, "updated_at": get_utc_now()})
        await self._save(job)
        return job

    async def _load(self, job_id: str) -> PdfJobView | None:
        raw = await self.redis.get(JOB_KEY.format(job_id))
        if not raw:
            return None
        try:
            return PdfJobView.model_validate(json.loads(raw))
        except (ValueError, TypeError):
            return None

    async def get(self, job_id: str) -> PdfJobView | None:
        job = await self._load(job_id)
        if job is None or job.status not in ACTIVE_STATUSES:
            return job
        idle = (get_utc_now() - job.updated_at).total_seconds()
        if idle > STALE_AFTER_SECONDS:
            return await self.update(job_id, status="failed", error=STALE_ERROR)
        return job

    async def recent(self) -> list[PdfJobView]:
        ids = await self.redis.zrevrange(JOBS_INDEX, 0, RECENT_LIMIT - 1)
        jobs: list[PdfJobView] = []
        stale: list[str] = []
        for raw_id in ids:
            job_id = raw_id.decode() if isinstance(raw_id, bytes) else str(raw_id)
            job = await self.get(job_id)
            if job is None:
                stale.append(job_id)  # TTL tugagan
            else:
                jobs.append(job)
        if stale:
            await self.redis.zrem(JOBS_INDEX, *stale)
        # Ro'yxat cheksiz o'smasin
        await self.redis.zremrangebyrank(JOBS_INDEX, 0, -(RECENT_LIMIT * 5) - 1)
        return jobs


OnDone = Callable[[PdfUploadResult], Awaitable[None]]


async def run_pdf_job(
    jobs: PdfJobStore,
    job_id: str,
    use_case: UploadPdfUseCase,
    content: bytes,
    filename: str,
    title: str,
    on_done: OnDone,
) -> None:
    """Ishni bajaradi va holatni yangilab boradi. Xato foydalanuvchiga
    holat orqali ko'rinadi (so'rov allaqachon tugagan)."""
    async with _SEMAPHORE:
        await jobs.update(job_id, status="running", stage="reading")

        async def progress(stage: str, done: int, total: int) -> None:
            await jobs.update(job_id, stage=stage, done=done, total=total)

        try:
            result = await use_case.execute(
                file_bytes=content, filename=filename, title=title, progress=progress
            )
        except Exception as exc:  # noqa: BLE001 — holatga yoziladi
            # Biznes xatosi (matn topilmadi va h.k.) — matni admin uchun foydali.
            # Boshqasi (Ollama/Qdrant) — umumiy matn: xom xatoda ichki manzillar
            # bo'lishi mumkin, tafsilot faqat logda.
            message = (
                exc.message
                if isinstance(exc, InstanceProcessingException) and exc.message
                else FAILED_ERROR
            )
            logger.exception("[PDF] fon ishi yiqildi: %s (%s)", filename, job_id)
            await jobs.update(job_id, status="failed", error=message[:500])
            return
        await jobs.update(job_id, status="done", stage="", result=result, title=result.title)
    try:
        await on_done(result)
    except Exception:  # noqa: BLE001 — bildirishnoma natijani buzmasin
        logger.exception("[PDF] yakuniy bildirishnoma yuborilmadi: %s", job_id)


def schedule_pdf_job(
    jobs: PdfJobStore,
    job_id: str,
    use_case: UploadPdfUseCase,
    content: bytes,
    filename: str,
    title: str,
    on_done: OnDone,
) -> None:
    task = asyncio.create_task(
        run_pdf_job(jobs, job_id, use_case, content, filename, title, on_done)
    )
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def notify_admins_updated(result: PdfUploadResult) -> None:
    """"Ma'lumotlar yangilandi" — adminlarga. So'rov allaqachon tugagan,
    uning DB sessiyasi yopiq — yangi sessiya ochiladi."""
    async with async_session() as session:
        uow = await get_uow(session)
        await BroadcastNotificationUseCase(uow=uow).execute(
            NotificationType.KNOWLEDGE_UPDATED,
            params={"title": result.title},
            role=UserRole.ADMIN,
        )


class StartPdfUploadUseCase:
    """Faylni qabul qiladi va ishni fonda boshlaydi — darhol qaytadi."""

    def __init__(self, jobs: PdfJobStore, use_case: UploadPdfUseCase) -> None:
        self.jobs = jobs
        self.use_case = use_case

    async def execute(self, content: bytes, filename: str, title: str) -> PdfJobView:
        job = await self.jobs.create(filename, title.strip())
        schedule_pdf_job(
            self.jobs, job.id, self.use_case, content, filename, title, notify_admins_updated
        )
        return job


class PdfJobStatusUseCase:
    def __init__(self, jobs: PdfJobStore) -> None:
        self.jobs = jobs

    async def get(self, job_id: str) -> PdfJobView:
        job = await self.jobs.get(job_id)
        if job is None:
            raise InstanceNotFoundException(JOB_NOT_FOUND)
        return job

    async def recent(self) -> list[PdfJobView]:
        return await self.jobs.recent()


# ---- DI ----


def get_pdf_job_store(redis: Redis = Depends(get_redis_client)) -> PdfJobStore:
    return PdfJobStore(redis)


def get_start_pdf_upload_use_case(
    jobs: PdfJobStore = Depends(get_pdf_job_store),
    embedder: OllamaEmbedder = Depends(get_embedder),
    store: QdrantStore = Depends(get_vector_store),
    ai_client: BaseAIClient = Depends(get_ai_client),
) -> StartPdfUploadUseCase:
    # embedder/store/ai_client ilova umri davomida yashaydigan HTTP klient
    # ustida — so'rov tugagach ham fon ishida ishlatish xavfsiz
    return StartPdfUploadUseCase(
        jobs, UploadPdfUseCase(embedder=embedder, store=store, ai_client=ai_client)
    )


def get_pdf_job_status_use_case(
    jobs: PdfJobStore = Depends(get_pdf_job_store),
) -> PdfJobStatusUseCase:
    return PdfJobStatusUseCase(jobs)

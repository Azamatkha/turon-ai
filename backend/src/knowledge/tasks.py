"""Kunlik vazifa: valyuta kurslarini scrape qilib vektor bazaga yozadi.

Har kuni Toshkent vaqti bilan 11:00 da (Celery timezone UTC — 06:00 UTC)
ishga tushadi. Eski kurslar o'chirilib, yangisi yoziladi — bazada har doim
faqat joriy kurs turadi.
"""

import base64

import httpx

from celery_tasks.main import celery_app  # noqa: F401
from celery_tasks.types import typed_shared_task
from loggers import get_logger
from src.core.ai.clients.ollama import OllamaClient
from src.core.ai.embeddings import OllamaEmbedder
from src.core.redis.core import create_redis_client
from src.core.utils.coroutine_runner import execute_coroutine_sync
from src.core.vectorstore.qdrant_store import QdrantStore
from src.knowledge.pdf_jobs import clear_pdf, load_pdf, set_status
from src.knowledge.rates_scraper import RATES_TITLE, RATES_URL, parse_rates
from src.knowledge.scraper import fetch_html
from src.knowledge.usecases import UploadKnowledgeUseCase, UploadPdfUseCase
from src.main.config import config

logger = get_logger(__name__)


# PDF ishlash uzoq (OCR + har bo'lakni LLM tozalashi) — httpx timeout keng.
_PDF_HTTP_TIMEOUT = 600


@typed_shared_task(name="process_pdf")
def process_pdf(job_id: str, filename: str, title: str) -> str:
    """PDF hujjatni fon rejimida o'qib bazaga yozadi (60s proxy cheklovidan
    qochish uchun). Holat Redis'ga yoziladi — frontend shundan kuzatadi."""
    return execute_coroutine_sync(
        coroutine=lambda: _process_pdf(job_id, filename, title)
    )


async def _process_pdf(job_id: str, filename: str, title: str) -> str:
    redis = create_redis_client(connection_url=config.redis.dsn)
    try:
        await set_status(
            redis, job_id, state="processing", message="Hujjat o'qilmoqda…"
        )
        pdf_b64 = await load_pdf(redis, job_id)
        if not pdf_b64:
            await set_status(
                redis,
                job_id,
                state="error",
                error="PDF topilmadi (muddati o'tgan). Qayta yuklang.",
            )
            return "no data"

        file_bytes = base64.b64decode(pdf_b64)
        async with httpx.AsyncClient(timeout=_PDF_HTTP_TIMEOUT) as http:
            embedder = OllamaEmbedder(http=http)
            store = QdrantStore()
            ai_client = OllamaClient(http=http)
            use_case = UploadPdfUseCase(
                embedder=embedder, store=store, ai_client=ai_client
            )
            result = await use_case.execute(
                file_bytes=file_bytes, filename=filename, title=title
            )

        await set_status(
            redis,
            job_id,
            state="done",
            message="Tayyor",
            title=result.title,
            pages=result.pages,
            ocr_pages=result.ocr_pages,
            chunks=result.chunks,
        )
        await clear_pdf(redis, job_id)
        logger.info("PDF ishlandi (job %s): %s bo'lak", job_id, result.chunks)
        return f"done: {result.chunks} chunks"
    except Exception as exc:
        logger.exception("PDF ishlashda xato (job %s)", job_id)
        await set_status(
            redis,
            job_id,
            state="error",
            error=f"{type(exc).__name__}: {exc}",
        )
        await clear_pdf(redis, job_id)
        return f"error: {exc}"
    finally:
        await redis.aclose()


@typed_shared_task(name="scrape_exchange_rates")
def scrape_exchange_rates() -> str:
    return execute_coroutine_sync(coroutine=_scrape_exchange_rates)


async def _scrape_exchange_rates() -> str:
    html = await fetch_html(RATES_URL)
    text = parse_rates(html)
    if not text.strip():
        logger.warning(
            "Valyuta kurslari topilmadi — sahifa tuzilishi o'zgargan bo'lishi mumkin: %s",
            RATES_URL,
        )
        return "no rates parsed"

    store = QdrantStore()
    async with httpx.AsyncClient() as http:
        embedder = OllamaEmbedder(http=http)

        # Eski kurs yozuvlarini id bo'yicha o'chiramiz (payload-filtr indeksiga
        # bog'liq emas) — kurslar har kuni o'zgaradi, eskisi qolib ketmasin.
        existing = await store.scroll_all_records(limit=10000)
        stale = [pid for pid, p in existing if p.get("title") == RATES_TITLE]
        await store.delete_ids(stale)

        result = await UploadKnowledgeUseCase(embedder=embedder, store=store).execute(
            title=RATES_TITLE, text=text, source_url=RATES_URL
        )

    logger.info("Valyuta kurslari yangilandi: %s bo'lak", result.chunks)
    return f"rates updated: {result.chunks} chunks"

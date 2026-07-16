"""Kunlik vazifa: valyuta kurslarini scrape qilib vektor bazaga yozadi.

Har kuni Toshkent vaqti bilan 11:00 da (Celery timezone UTC — 06:00 UTC)
ishga tushadi. Eski kurslar o'chirilib, yangisi yoziladi — bazada har doim
faqat joriy kurs turadi.
"""

import httpx

from celery_tasks.main import celery_app  # noqa: F401
from celery_tasks.types import typed_shared_task
from loggers import get_logger
from src.core.ai.embeddings import OllamaEmbedder
from src.core.utils.coroutine_runner import execute_coroutine_sync
from src.core.vectorstore.qdrant_store import QdrantStore
from src.knowledge.rates_scraper import RATES_TITLE, RATES_URL, parse_rates
from src.knowledge.scraper import fetch_html
from src.knowledge.usecases import UploadKnowledgeUseCase

logger = get_logger(__name__)


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

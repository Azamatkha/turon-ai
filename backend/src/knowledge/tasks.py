"""Kunlik vazifa: valyuta kurslarini scrape qilib vektor bazaga yozadi.

Har kuni Toshkent vaqti bilan 11:00 da (Celery timezone UTC — 06:00 UTC)
ishga tushadi. Eski kurslar o'chirilib, yangisi yoziladi — bazada har doim
faqat joriy kurs turadi.
"""

from typing import Any

import httpx

from celery_tasks.main import celery_app, local_async_session  # noqa: F401
from celery_tasks.types import typed_shared_task
from loggers import get_logger
from src.core.ai.embeddings import OllamaEmbedder
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.utils.coroutine_runner import execute_coroutine_sync
from src.core.vectorstore.qdrant_store import QdrantStore
from src.knowledge.rates_scraper import RATES_TITLE, RATES_URL, parse_rates
from src.knowledge.scraper import fetch_html
from src.knowledge.usecases import UploadKnowledgeUseCase
from src.notifications.enums import NotificationType
from src.notifications.events import publish_new

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
        stale = [(pid, p) for pid, p in existing if p.get("title") == RATES_TITLE]
        old_text = _join_chunks([p for _, p in stale])
        await store.delete_ids([pid for pid, _ in stale])

        result = await UploadKnowledgeUseCase(embedder=embedder, store=store).execute(
            title=RATES_TITLE, text=text, source_url=RATES_URL
        )

    logger.info("Valyuta kurslari yangilandi: %s bo'lak", result.chunks)

    # Bildirishnoma faqat kurs haqiqatan o'zgargandagina — vazifa har kuni
    # ishlaydi, kurs esa har kuni o'zgaravermaydi.
    if _squash(text) != _squash(old_text):
        await _broadcast_rates_updated()

    return f"rates updated: {result.chunks} chunks"


def _join_chunks(payloads: list[dict[str, Any]]) -> str:
    """Bir sarlavha ostidagi bo'laklarni tartib bilan bitta matnga yig'adi."""
    ordered = sorted(payloads, key=lambda p: int(p.get("chunk_index", 0) or 0))
    return "\n".join(str(p.get("chunk_text", "")) for p in ordered)


def _squash(value: str) -> str:
    """Solishtirish uchun bo'sh joylarni normallashtiradi."""
    return " ".join(value.split())


async def _broadcast_rates_updated() -> None:
    """Barcha aktiv foydalanuvchilarga "valyuta kursi o'zgardi" xabarini yozadi."""
    try:
        async with local_async_session() as session:
            uow: ApplicationUnitOfWork[RepositoryProtocol] = ApplicationUnitOfWork(
                session
            )
            async with uow:
                recipients = await uow.notifications.fan_out(
                    uow.session, notification_type=NotificationType.RATES_UPDATED
                )
                await uow.commit()
        await publish_new(recipients)
        logger.info(
            "Valyuta kursi bildirishnomasi yuborildi: %s foydalanuvchi",
            len(recipients),
        )
    except Exception:
        logger.exception("Valyuta kursi bildirishnomasini yuborib bo'lmadi")

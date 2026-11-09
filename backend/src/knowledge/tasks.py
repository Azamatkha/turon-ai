"""Kunlik vazifa: valyuta kurslarini scrape qilib vektor bazaga yozadi.

Har kuni Toshkent vaqti bilan 09:05–12:35 oralig'ida har yarim soatda ishga
tushadi (jadval: celery_tasks/main.py). Kurs o'zgarmagan bo'lsa hech narsa
yozilmaydi; o'zgargan bo'lsa yangisi eskisining ustiga yoziladi — bazada har
doim faqat joriy kurs turadi.
"""

import json
from typing import Any

import httpx

from celery_tasks.main import celery_app, local_async_session  # noqa: F401
from celery_tasks.types import typed_shared_task
from loggers import get_logger
from src.core.ai.embeddings import OllamaEmbedder
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.redis.core import create_redis_client
from src.core.utils.coroutine_runner import execute_coroutine_sync
from src.core.utils.datetime_utils import get_utc_now
from src.core.vectorstore.qdrant_store import QdrantStore
from src.knowledge.rates_scraper import (
    RATES_TITLE,
    RATES_URL,
    apply_deltas,
    parse_rates_structured,
    render_rates,
)
from src.knowledge.rescrape import (
    RESCRAPE_LAST_KEY,
    RESCRAPE_RUNNING_KEY,
    RescrapeKnowledgeUseCase,
)
from src.knowledge.scraper import fetch_html
from src.knowledge.usecases import UploadKnowledgeUseCase
from src.knowledge.validity import WARN_DAYS, expiry_events
from src.main.config import config
from src.notifications.enums import NotificationType
from src.notifications.events import publish_new
from src.user.enums import UserRole

logger = get_logger(__name__)


@typed_shared_task(name="scrape_exchange_rates")
def scrape_exchange_rates() -> str:
    return execute_coroutine_sync(coroutine=_scrape_exchange_rates)


async def _scrape_exchange_rates() -> str:
    html = await fetch_html(RATES_URL)
    current = parse_rates_structured(html)
    if not current.get("channels"):
        logger.warning(
            "Valyuta kurslari topilmadi — sahifa tuzilishi o'zgargan bo'lishi mumkin: %s",
            RATES_URL,
        )
        return "no rates parsed"

    store = QdrantStore()
    async with httpx.AsyncClient() as http:
        embedder = OllamaEmbedder(http=http)

        existing = await store.scroll_all_records(limit=10000)
        stale = [(pid, p) for pid, p in existing if p.get("title") == RATES_TITLE]
        old_text = _join_chunks([p for _, p in stale])
        # Oldingi strukturali kurslar — bugungi kurs kechagisiga nisbatan
        # qancha o'zgarganini shu asosda hisoblaymiz.
        previous = _stored_rates([p for _, p in stale])

        # Saytdagi kurs bazadagi bilan AYNAN bir xil (dam olish kuni yoki bank
        # hali yangilamagan) — hech narsa yozmaymiz. Ilgari bunday kuni ham
        # qayta yozilardi: sana o'zgarmagani uchun delta hisoblanmasdi, oynadagi
        # ▲/▼ belgilari o'chib ketardi, matn esa "o'zgargan" bo'lib ko'rinib,
        # hammaga soxta "kurs o'zgardi" bildirishnomasi borardi. Shu tekshiruv
        # tufayli vazifani kuniga bir necha marta ishlatish ham xavfsiz.
        if previous is not None and _same_rates(current, previous):
            logger.info(
                "Valyuta kurslari o'zgarmagan (%s) — yozilmadi", current.get("stamp")
            )
            return "rates unchanged"

        current = apply_deltas(current, previous)
        text = render_rates(current)

        # TARTIB MUHIM: avval YOZAMIZ, keyin ortiqchasini o'chiramiz.
        # Ilgari eski kurs OLDIN o'chirilardi — embedding (Ollama) yoki Qdrant
        # o'sha paytda javob bermasa, eski kurs yo'qolib, yangisi yozilmay
        # qolardi va /v1/chat/rates bo'sh qaytarardi. Endi yozish yiqilsa,
        # kechagi kurs joyida qoladi.
        result = await UploadKnowledgeUseCase(embedder=embedder, store=store).execute(
            title=RATES_TITLE,
            text=text,
            source_url=RATES_URL,
            # Matn bilan bir qatorda strukturali ko'rinish ham saqlanadi —
            # kurs oynasi (modal) shu JSON'ni o'qiydi, alohida jadval kerak emas.
            extra_payload={"rates_json": json.dumps(current, ensure_ascii=False)},
        )

        # Point ID = title + chunk_index (QdrantStore._stable_id), ya'ni yangi
        # bo'laklar eskilarining USTIGA yozildi. Faqat yangisida yo'q bo'lgan
        # (kechagi matn uzunroq bo'lgan) bo'laklar qoladi — shularni o'chiramiz.
        leftover = [
            pid for pid, p in stale
            if int(p.get("chunk_index", 0) or 0) >= result.chunks
        ]
        await store.delete_ids(leftover)

    logger.info("Valyuta kurslari yangilandi: %s bo'lak", result.chunks)

    # Bildirishnoma faqat kurs haqiqatan o'zgargandagina — vazifa har kuni
    # ishlaydi, kurs esa har kuni o'zgaravermaydi.
    if _squash(text) != _squash(old_text):
        await _broadcast_rates_updated()

    return f"rates updated: {result.chunks} chunks"


def _stored_rates(payloads: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Payload'da saqlangan strukturali kurslarni qaytaradi (birinchi topilgani —
    barcha bo'laklarda bir xil). Eski yozuvlarda bu maydon bo'lmasligi mumkin."""
    for p in payloads:
        raw = p.get("rates_json")
        if not raw:
            continue
        try:
            data: dict[str, Any] = json.loads(str(raw))
        except json.JSONDecodeError:
            logger.warning("rates_json o'qib bo'lmadi — farq hisoblanmaydi")
            return None
        return data
    return None


def _rates_core(data: dict[str, Any]) -> list[Any]:
    """Solishtirish uchun kurslarning "sof" ko'rinishi: sana + har kanal
    qatorlari, `delta_*` maydonlarisiz (ular bizda hisoblanadi, saytda yo'q)."""
    return [
        data.get("stamp"),
        [
            (
                ch.get("key"),
                [
                    {k: v for k, v in row.items() if not k.startswith("delta_")}
                    for row in ch.get("rows", [])
                ],
            )
            for ch in data.get("channels", [])
        ],
    ]


def _same_rates(current: dict[str, Any], previous: dict[str, Any]) -> bool:
    return _rates_core(current) == _rates_core(previous)


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


# ---- Hujjatlarning amal qilish muddati ----


@typed_shared_task(name="check_knowledge_validity")
def check_knowledge_validity() -> str:
    soon, expired = execute_coroutine_sync(coroutine=_check_knowledge_validity)
    return f"expiring={len(soon)} expired={len(expired)}"


async def _check_knowledge_validity() -> tuple[list[str], list[str]]:
    """Muddati WARN_DAYS kundan keyin tugaydigan va bugun tugagan hujjatlar
    haqida adminlarga BITTA bildirishnoma (har tur uchun).

    Faqat aniq shu ikki kunda yuboriladi (validity.expiry_events) — har kuni
    bir xil xabar takrorlanmaydi."""
    store = QdrantStore()
    if not await store.exists():
        return [], []
    soon, expired = expiry_events(await store.scroll_all_pages())
    for kind, titles in (
        (NotificationType.KNOWLEDGE_EXPIRING, soon),
        (NotificationType.KNOWLEDGE_EXPIRED, expired),
    ):
        if titles:
            await _notify_admins(
                kind,
                {"title": titles[0], "count": str(len(titles)), "days": str(WARN_DAYS)},
            )
    if soon or expired:
        logger.info("Hujjat muddati: %d ta yaqin, %d ta tugagan", len(soon), len(expired))
    return soon, expired


async def _notify_admins(notification_type: str, params: dict[str, str]) -> None:
    try:
        async with local_async_session() as session:
            uow: ApplicationUnitOfWork[RepositoryProtocol] = ApplicationUnitOfWork(
                session
            )
            async with uow:
                recipients = await uow.notifications.fan_out(
                    uow.session,
                    notification_type=notification_type,
                    params=params,
                    role=UserRole.ADMIN,
                )
                await uow.commit()
        await publish_new(recipients)
    except Exception:
        logger.exception("Muddat bildirishnomasini yuborib bo'lmadi: %s", notification_type)


# ---- Saytdan olingan hujjatlarni qayta tekshirish ----


@typed_shared_task(name="rescrape_knowledge")
def rescrape_knowledge(manual: bool = False) -> str:
    # Avtomatik ishga tushish sozlamada o'chirilgan bo'lsa — faqat qo'lda
    if not manual and not config.scraping.RESCRAPE_ENABLED:
        return "disabled"
    return execute_coroutine_sync(coroutine=_rescrape_knowledge)


async def _rescrape_knowledge() -> str:
    redis = create_redis_client(config.redis.dsn)
    try:
        # Bir vaqtda ikkita ishga tushmasin (qo'lda + jadval)
        if not await redis.set(RESCRAPE_RUNNING_KEY, "1", nx=True, ex=3600):
            return "already running"
        started = get_utc_now()
        store = QdrantStore()
        async with httpx.AsyncClient() as http:
            summary = await RescrapeKnowledgeUseCase(
                embedder=OllamaEmbedder(http=http), store=store
            ).execute()
        await redis.set(
            RESCRAPE_LAST_KEY,
            json.dumps(
                {
                    "started_at": started.isoformat(),
                    "finished_at": get_utc_now().isoformat(),
                    "checked": summary.checked,
                    "unchanged": summary.unchanged,
                    "changed": summary.changed,
                    "failed": [{"title": t, "error": e} for t, e in summary.failed],
                },
                ensure_ascii=False,
            ),
        )
    finally:
        await redis.delete(RESCRAPE_RUNNING_KEY)
        await redis.aclose()

    if summary.changed:
        await _notify_admins(
            NotificationType.KNOWLEDGE_UPDATED,
            {"title": summary.changed[0], "count": str(len(summary.changed))},
        )
    if summary.failed:
        await _notify_admins(
            NotificationType.KNOWLEDGE_SOURCE_FAILED,
            {"title": summary.failed[0][0], "count": str(len(summary.failed))},
        )
    logger.info(
        "Qayta scraping: %d tekshirildi, %d o'zgardi, %d xato",
        summary.checked,
        len(summary.changed),
        len(summary.failed),
    )
    return f"checked={summary.checked} changed={len(summary.changed)} failed={len(summary.failed)}"

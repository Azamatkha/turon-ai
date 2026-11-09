"""Bilim bazasini saytdan avtomatik yangilash va dublikatlarni topish.

Qayta scraping: `source_url`i bor har bir hujjat sahifasi qayta ochiladi.
Yangi matn AYNAN yuklashdagi kabi bo'laklanadi (`chunk_text` deterministik)
va bazadagi bo'laklar bilan solishtiriladi — faqat farq bo'lsa hujjat qayta
yoziladi (embedding qimmat: o'zgarmagan sahifaga model chaqirilmaydi).
Sarlavha, havola va amal qilish muddati saqlanadi.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

from fastapi import Depends
from redis.asyncio import Redis

from loggers import get_logger
from src.core.ai.embeddings import OllamaEmbedder
from src.core.redis.dependencies import get_redis_client
from src.core.vectorstore.qdrant_store import QdrantStore
from src.knowledge.chunking import chunk_text
from src.knowledge.rates_scraper import RATES_TITLE
from src.knowledge.schemas import RescrapeResultView, RescrapeStatusView
from src.knowledge.scraper import extract_content, fetch_html
from src.main.config import config

logger = get_logger(__name__)

_SPACES = re.compile(r"\s+")

# Oxirgi natija (admin panel ko'rsatadi) va "hozir ishlayapti" belgisi — Redis
RESCRAPE_LAST_KEY = "knowledge:rescrape:last"
RESCRAPE_RUNNING_KEY = "knowledge:rescrape:running"


@dataclass
class RescrapeSummary:
    checked: int = 0
    unchanged: int = 0
    changed: list[str] = field(default_factory=list)
    # (sarlavha, xato turi) — sahifa ochilmadi yoki matn chiqmadi
    failed: list[tuple[str, str]] = field(default_factory=list)


def group_by_title(payloads: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for p in payloads:
        groups.setdefault(str(p.get("title", "")), []).append(p)
    for chunks in groups.values():
        chunks.sort(key=lambda p: int(p.get("chunk_index", 0) or 0))
    return groups


def scrape_targets(groups: dict[str, list[dict[str, Any]]]) -> list[tuple[str, str]]:
    """(sarlavha, havola) — qayta tekshiriladigan hujjatlar.

    Valyuta kurslari o'z vazifasida yangilanadi, xodimlar va PDF'larda
    havola yo'q — ular kirmaydi."""
    targets = []
    for title, chunks in groups.items():
        url = next((str(c.get("source_url") or "") for c in chunks if c.get("source_url")), "")
        if not title or title == RATES_TITLE or not url.startswith(("http://", "https://")):
            continue
        if any(c.get("doc_type") == "employee" for c in chunks):
            continue
        targets.append((title, url))
    return targets


def content_changed(stored_chunks: list[dict[str, Any]], new_text: str) -> bool:
    """Yangi matnning bo'laklari bazadagidan farq qiladimi."""
    stored = [str(c.get("chunk_text", "")) for c in stored_chunks]
    return stored != chunk_text(new_text)


def normalized_hash(chunks: list[dict[str, Any]]) -> str:
    """Hujjat matnining "barmoq izi": kichik harf, bo'shliqlar bitta.
    Bir xil matn turli sarlavha bilan ikki marta yuklansa — hash bir xil."""
    text = " ".join(str(c.get("chunk_text", "")) for c in chunks)
    norm = _SPACES.sub(" ", text.lower()).strip()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def find_duplicates(groups: dict[str, list[dict[str, Any]]]) -> dict[str, list[str]]:
    """sarlavha -> matni AYNAN bir xil bo'lgan boshqa sarlavhalar."""
    by_hash: dict[str, list[str]] = {}
    for title, chunks in groups.items():
        if not title or not any(str(c.get("chunk_text", "")).strip() for c in chunks):
            continue
        by_hash.setdefault(normalized_hash(chunks), []).append(title)
    result: dict[str, list[str]] = {}
    for titles in by_hash.values():
        if len(titles) < 2:
            continue
        for t in titles:
            result[t] = sorted(x for x in titles if x != t)
    return result


class RescrapeKnowledgeUseCase:
    def __init__(self, embedder: OllamaEmbedder, store: QdrantStore) -> None:
        self.embedder = embedder
        self.store = store

    async def execute(self) -> RescrapeSummary:
        # Import shu yerda: usecases.py bu moduldan oldin yuklanadi (sikl bo'lmasin)
        from src.knowledge.usecases import UpdateKnowledgeUseCase

        summary = RescrapeSummary()
        if not await self.store.exists():
            return summary
        groups = group_by_title(await self.store.scroll_all_pages())
        for title, url in scrape_targets(groups):
            summary.checked += 1
            try:
                html = await fetch_html(url)
                _, text = extract_content(html, url)
            except Exception as exc:  # noqa: BLE001 - bitta sahifa qolganlarini to'xtatmasin
                logger.warning("Qayta scraping: %s ochilmadi: %r", url, exc)
                summary.failed.append((title, type(exc).__name__))
                continue
            if not text:
                # Sahifa bo'sh qaytdi (vaqtincha xato yoki tuzilma o'zgardi) —
                # bazadagi ishlaydigan matnni bo'sh bilan almashtirmaymiz
                summary.failed.append((title, "empty"))
                continue
            if not content_changed(groups[title], text):
                summary.unchanged += 1
                continue
            await UpdateKnowledgeUseCase(embedder=self.embedder, store=self.store).execute(
                old_title=title, title=title, text=text
            )
            summary.changed.append(title)
            logger.info("Qayta scraping: yangilandi — %s", title)
        return summary


class RescrapeStatusUseCase:
    """Admin panel uchun: hozir ishlayaptimi va oxirgi natija."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def execute(self) -> RescrapeStatusView:
        running = bool(await self.redis.exists(RESCRAPE_RUNNING_KEY))
        raw = await self.redis.get(RESCRAPE_LAST_KEY)
        last = None
        if raw:
            try:
                last = RescrapeResultView.model_validate(json.loads(raw))
            except ValueError:
                logger.warning("Qayta scraping natijasi o'qilmadi")
        return RescrapeStatusView(
            enabled=config.scraping.RESCRAPE_ENABLED, running=running, last=last
        )


class TriggerRescrapeUseCase:
    """Qayta tekshiruvni hoziroq navbatga qo'yadi (Celery worker bajaradi)."""

    def execute(self) -> None:
        from src.knowledge.tasks import rescrape_knowledge

        rescrape_knowledge.delay(manual=True)


def get_rescrape_status_use_case(
    redis: Redis = Depends(get_redis_client),
) -> RescrapeStatusUseCase:
    return RescrapeStatusUseCase(redis)

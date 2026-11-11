"""Bazada javob topilmasa — ruxsat etilgan saytlardan qidirish.

Ollama modeli internetga o'zi chiqmaydi. Shu modul:
1. O'z serverimizdagi SearXNG'dan natija so'raydi (faqat `site:` domenlar);
2. natija URL'larini KODDA ham allowlist bo'yicha qayta tekshiradi —
   SearXNG yoki qidiruv dvigateli boshqa saytni qaytarsa ham, u tashlanadi;
3. har sahifani mavjud scraper (fetch_html + extract_content) bilan oladi.

Maxfiylik: tashqariga foydalanuvchining xom savoli emas, router tozalagan
qidiruv so'rovi PII maskalangan holda ketadi (qara: usecases._web_fallback).
Xato bo'lsa (SearXNG o'chiq, timeout) — bo'sh ro'yxat, javob yiqilmaydi.
"""

import asyncio
from dataclasses import dataclass
import time
from urllib.parse import urlparse

import httpx

from loggers import get_logger
from src.core.ai.guard import mask_pii
from src.knowledge.scraper import extract_content, fetch_html
from src.main.config import config

logger = get_logger(__name__)

# Bir xil so'rov qayta-qayta kelsa SearXNG va saytlarni bezovta qilmaymiz.
# Jarayon ichidagi oddiy kesh: 24 soat, eng ko'pi 200 ta yozuv.
_CACHE_TTL = 24 * 3600
_CACHE_MAX = 200
_cache: dict[str, tuple[float, list["WebHit"]]] = {}


@dataclass(frozen=True)
class WebHit:
    url: str
    title: str
    text: str

    @property
    def domain(self) -> str:
        return (urlparse(self.url).hostname or "").removeprefix("www.")


def is_allowed_url(url: str, domains: list[str] | None = None) -> bool:
    """URL ruxsat etilgan domen (yoki uning subdomeni) va http(s)mi."""
    allowed = domains if domains is not None else config.web_search.allowed_domains
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower().rstrip(".")
    return any(host == d or host.endswith("." + d) for d in allowed)


def build_query(query: str, domains: list[str]) -> str:
    sites = " OR ".join(f"site:{d}" for d in domains)
    return f"{query} ({sites})" if sites else query


async def _searxng(query: str) -> list[tuple[str, str]]:
    """SearXNG'dan (url, sarlavha) ro'yxati — allowlist'dan o'tganlari."""
    cfg = config.web_search
    domains = cfg.allowed_domains
    async with httpx.AsyncClient(timeout=cfg.WEB_SEARCH_TIMEOUT_SECONDS) as client:
        resp = await client.get(
            f"{cfg.SEARXNG_URL.rstrip('/')}/search",
            params={"q": build_query(query, domains), "format": "json", "safesearch": 1},
        )
        resp.raise_for_status()
        data = resp.json()
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item in data.get("results") or []:
        url = str(item.get("url") or "")
        if not url or url in seen or not is_allowed_url(url, domains):
            continue
        seen.add(url)
        out.append((url, str(item.get("title") or "")))
        if len(out) >= cfg.WEB_SEARCH_MAX_RESULTS:
            break
    return out


async def _page(url: str, title: str) -> WebHit | None:
    cfg = config.web_search
    try:
        html = await fetch_html(url, timeout=int(cfg.WEB_SEARCH_TIMEOUT_SECONDS) + 2)
        page_title, text = extract_content(html, url)
    except Exception as exc:  # noqa: BLE001 - bitta sahifa ochilmasa, qolganlari bilan
        logger.info("Veb sahifa olinmadi %s: %s", url, exc)
        return None
    text = text.strip()
    if len(text) < 80:
        return None
    return WebHit(url=url, title=(title or page_title or url)[:300], text=text[: cfg.WEB_SEARCH_PAGE_CHARS])


async def search(query: str) -> list[WebHit]:
    """Qidiruv + sahifa matnlari. O'chiq yoki xato bo'lsa — []."""
    cfg = config.web_search
    if not cfg.WEB_SEARCH_ENABLED or not cfg.allowed_domains:
        return []
    query = mask_pii(query.strip())[0][:300]
    if len(query) < 3:
        return []
    key = query.lower()
    now = time.monotonic()
    cached = _cache.get(key)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]
    try:
        found = await _searxng(query)
    except Exception as exc:  # noqa: BLE001 - qidiruv ishlamasa ham javob yiqilmaydi
        logger.warning("Veb-qidiruv ishlamadi: %s", exc)
        return []
    pages = await asyncio.gather(*(_page(u, t) for u, t in found))
    hits = [p for p in pages if p is not None]
    logger.info("Veb-qidiruv %r: %d natija, %d sahifa", query, len(found), len(hits))
    if len(_cache) >= _CACHE_MAX:
        _cache.pop(next(iter(_cache)))
    _cache[key] = (now, hits)
    return hits

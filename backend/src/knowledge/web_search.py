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
from src.core.utils.uzbek_script import is_cyrillic_text, to_cyrillic
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


async def _ask(client: httpx.AsyncClient, q: str) -> list[dict]:
    """Bitta SearXNG so'rovi — xom natijalar (xato bo'lsa bo'sh)."""
    cfg = config.web_search
    try:
        resp = await client.get(
            f"{cfg.SEARXNG_URL.rstrip('/')}/search",
            params={"q": q, "format": "json", "safesearch": 1},
        )
        resp.raise_for_status()
        return list(resp.json().get("results") or [])
    except Exception as exc:  # noqa: BLE001 - bitta bosqich yiqilsa, keyingisi bor
        logger.info("SearXNG so'rovi ishlamadi %r: %s", q[:120], exc)
        return []


def _allowed(results: list[dict], domains: list[str], limit: int) -> list[tuple[str, str]]:
    """Natijalardan faqat ruxsat etilgan domenlar — (url, sarlavha), takrorsiz."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item in results:
        url = str(item.get("url") or "")
        if not url or url in seen or not is_allowed_url(url, domains):
            continue
        seen.add(url)
        out.append((url, str(item.get("title") or "")))
        if len(out) >= limit:
            break
    return out


# Domen bo'yicha so'rovlar shu o'lchamdagi guruhlar bilan ketadi. Serverdagi
# diagnostika (2026-11-16): ketma-ket 3 ta so'rovdan keyin qidiruv tizimlari
# cheklay boshladi (keyingi hammasi 0 natija) — 22 tasini birdan yuborish
# o'zimizni bloklatadi.
_DOMAIN_BATCH = 3
# Butun qidiruv (barcha bosqichlar) uchun vaqt chegarasi — foydalanuvchi
# javobni cheksiz kutmasin
_SEARCH_BUDGET_SECONDS = 20.0


def _search_plan(query: str, domains: list[str]) -> list[list[str]]:
    """Qidiruv bosqichlari — har biri bir vaqtda yuboriladigan so'rovlar guruhi.

    Bosqichma-bosqich, chunki serverdagi qidiruv tizimlari bir nechta `site:`
    ni OR bilan yaxshi bajarmaydi (Google esa server IP'sini bloklagan):
      har alifbo varianti uchun (avval lotin, keyin kirill):
        1) bitta so'rov, barcha domenlar OR bilan;
        2) har domen alohida `site:` bilan — 3 tadan guruh;
      oxirida: filtrsiz so'rov, natijadan faqat ruxsat etilganlar."""
    variants = script_variants(query)
    plan: list[list[str]] = []
    for v in variants:
        plan.append([build_query(v, domains)])
        site_queries = [f"{v} site:{d}" for d in domains]
        plan.extend(
            site_queries[i : i + _DOMAIN_BATCH]
            for i in range(0, len(site_queries), _DOMAIN_BATCH)
        )
    plan.append(variants)
    return plan


async def _searxng(query: str) -> list[tuple[str, str]]:
    """SearXNG'dan (url, sarlavha) ro'yxati — allowlist'dan o'tganlari.

    Bosqichlar (`_search_plan`) navbat bilan yuboriladi va NATIJA TOPILISHI
    bilan to'xtaydi. Domen cheklovi har bosqichda KODDA tekshiriladi."""
    cfg = config.web_search
    domains = cfg.allowed_domains
    limit = cfg.WEB_SEARCH_MAX_RESULTS
    started = time.monotonic()
    async with httpx.AsyncClient(timeout=cfg.WEB_SEARCH_TIMEOUT_SECONDS) as client:
        for step, queries in enumerate(_search_plan(query, domains), 1):
            if time.monotonic() - started > _SEARCH_BUDGET_SECONDS:
                logger.info("Veb-qidiruv: vaqt tugadi (%d-bosqich) %r", step, query[:120])
                break
            answers = await asyncio.gather(*(_ask(client, q) for q in queries))
            found = _allowed([r for rs in answers for r in rs], domains, limit)
            if found:
                if step > 1:
                    logger.info("Veb-qidiruv: %d-bosqichda topildi %r", step, query[:120])
                return found
    return []


def script_variants(query: str) -> list[str]:
    """So'rov + uning ikkinchi alifbodagi varianti (o'zbekcha bo'lsa).

    lex.uz va davlat saytlaridagi hujjatlar ko'pincha KIRILLDA («Лотин
    ёзувига асосланган ўзбек алифбоси...»), qidiruv tizimlari esa lotin va
    kirillni turli so'z deb biladi — "lotin alifbosi site:lex.uz" 0 natija
    berardi.

    Faqat LOTINCHA so'rovga kirill varianti qo'shiladi. Kirillcha so'rov
    o'zgarishsiz: u ruscha bo'lishi mumkin (lotinga o'girilsa ma'nosiz), ruscha
    va o'zbek kirilini esa ishonchli ajratib bo'lmaydi; o'zbekcha savol baribir
    bot ichida lotinga keltiriladi."""
    if is_cyrillic_text(query):
        return [query]
    other = to_cyrillic(query)
    return [query] if other == query else [query, other]


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

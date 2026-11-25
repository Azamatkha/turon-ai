"""Rasmiy saytning "Yangiliklar" va "E'lonlar" bo'limlarini bilim bazasiga yuklash.

Bo'lim sahifasida faqat sarlavha va sana bor — asosiy matn har maqolaning
ICHKI sahifasida. Shuning uchun:
  1) ro'yxat sahifalari (?PAGEN_1=1, 2, ...) ochilib, maqola havolalari olinadi;
  2) har YANGI maqola ochiladi: sarlavha (h1), sana (meta datePublished),
     matn (.detail-text);
  3) maqola alohida yozuv bo'lib yoziladi: sarlavhada sana, turkumi
     "Yangiliklar" / "E'lonlar", doc_type=press.

Faqat yangilari yoziladi: bazada shu havola bor bo'lsa o'tkazib yuboriladi,
sahifadagi hamma maqola ma'lum bo'lsa — keyingi sahifalarga o'tilmaydi.
Birinchi ishga tushishda PRESS_MAX_AGE_DAYS kunlik arxiv olinadi.

Matn saytdagidek saqlanadi (ba'zi maqolalar o'zbek YANGI alifbosida:
"işonç", "Özbekiston") — qidiruv ikkala yozuvni ham tushunadi
(qara: uzbek_script.from_new_alphabet)."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from loggers import get_logger
from src.core.ai.embeddings import OllamaEmbedder
from src.core.vectorstore.qdrant_store import QdrantStore
from src.knowledge.categories import named_category_key
from src.knowledge.ingest_usecases import UploadKnowledgeUseCase
from src.knowledge.scraper import extract_content, fetch_html

logger = get_logger(__name__)

# Payload'dagi belgi: katalogga kirmaydi, haftalik qayta skanerlash tegmaydi
PRESS_DOC_TYPE = "press"
SITE = "https://turonbank.uz"


@dataclass(frozen=True)
class PressSection:
    path: str  # "/uz/press_center/news/"
    category_key: str
    category_name: str
    # Yozuv sarlavhasi boshidagi so'z: "Yangilik 22.11.2026: ..."
    label: str

    @property
    def list_url(self) -> str:
        return f"{SITE}{self.path}"


SECTIONS: tuple[PressSection, ...] = (
    PressSection("/uz/press_center/news/", "news", "Yangiliklar", "Yangilik"),
    PressSection("/uz/press_center/adverts/", "adverts", "E'lonlar", "E'lon"),
)


@dataclass
class PressArticle:
    url: str
    title: str
    published: date | None
    text: str


@dataclass
class PressSummary:
    checked: int = 0
    added: list[str] = field(default_factory=list)
    # (havola, xato turi)
    failed: list[tuple[str, str]] = field(default_factory=list)


def article_links(html: str, section: PressSection) -> list[str]:
    """Ro'yxat sahifasidagi maqola havolalari (to'liq URL, sahifadagi tartibda,
    takrorsiz). Bo'limning o'zi, RSS va sahifalash havolalari kirmaydi."""
    soup = BeautifulSoup(html, "html.parser")
    pattern = re.compile(rf"^{re.escape(section.path)}[^/?#]+/?$")
    out: list[str] = []
    for a in soup.find_all("a", href=True):
        parsed = urlparse(str(a["href"]))
        # Sahifalash havolalari ham maqola manzili ko'rinishida keladi
        # (".../slug?PAGEN_1=2") — so'rov qismi borlari maqola emas
        if parsed.query:
            continue
        path = parsed.path
        if not pattern.match(path) or path.rstrip("/").endswith("/rss"):
            continue
        url = urljoin(SITE, path if path.endswith("/") else f"{path}/")
        if url not in out:
            out.append(url)
    return out


# Saytdagi qisqa oy nomlari: "22 Noy 2026", "17 Okt 2025"
_MONTHS = {
    "yan": 1, "fev": 2, "mar": 3, "apr": 4, "may": 5, "iyun": 6,
    "iyul": 7, "avg": 8, "sen": 9, "okt": 10, "noy": 11, "dek": 12,
}
_DATE_TEXT_RE = re.compile(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})")


def _parse_date(soup: BeautifulSoup) -> date | None:
    meta = soup.find("meta", attrs={"itemprop": "datePublished"})
    if meta and meta.get("content"):
        try:
            return date.fromisoformat(str(meta["content"])[:10])
        except ValueError:
            pass
    el = soup.select_one(".post-date__text, .post-date, .news__date")
    m = _DATE_TEXT_RE.search(el.get_text(" ", strip=True)) if el else None
    if m:
        name = m.group(2).lower()
        # "Iyun"/"Iyul" — to'liq, qolganlari 3 harf ("Noyabr" ham bo'lishi mumkin)
        month = _MONTHS.get(name[:4]) or _MONTHS.get(name[:3])
        if month:
            try:
                return date(int(m.group(3)), month, int(m.group(1)))
            except ValueError:
                return None
    return None


_SPACES_RE = re.compile(r"[ \t\xa0]+")
_BLANKS_RE = re.compile(r"\n\s*\n\s*\n+")


def _body_text(soup: BeautifulSoup) -> str:
    """Maqola matni: <br> va bloklar — qator, jadval qatori — "a | b | c"."""
    body = soup.select_one(".detail-text") or soup.select_one("article")
    if body is None:
        return ""
    for tag in body.find_all(["script", "style"]):
        tag.decompose()
    for br in body.find_all("br"):
        br.replace_with("\n")
    for tr in body.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        tr.replace_with(" | ".join(c for c in cells if c) + "\n")
    for block in body.find_all(["p", "div", "li", "h2", "h3", "h4", "table"]):
        block.append("\n")
    lines = [_SPACES_RE.sub(" ", ln).strip() for ln in body.get_text().split("\n")]
    return _BLANKS_RE.sub("\n\n", "\n".join(lines)).strip()


def parse_article(html: str, url: str) -> PressArticle:
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else ""
    published = _parse_date(soup)
    text = _body_text(soup)
    if not title or not text:
        # Tuzilma o'zgargan bo'lsa — umumiy ajratuvchi (trafilatura)
        fb_title, fb_text = extract_content(html, url)
        title = title or fb_title
        text = text or fb_text
    return PressArticle(url=url, title=" ".join(title.split()), published=published, text=text)


def record_title(section: PressSection, a: PressArticle) -> str:
    day = a.published.strftime("%d.%m.%Y") if a.published else ""
    return f"{section.label} {day}: {a.title}" if day else f"{section.label}: {a.title}"


def record_text(section: PressSection, a: PressArticle) -> str:
    day = a.published.strftime("%d.%m.%Y") if a.published else "noma'lum"
    return (
        f"{section.category_name} (turonbank.uz). E'lon qilingan sana: {day}.\n"
        f"Sarlavha: {a.title}\n\n{a.text}"
    )


def known_urls(payloads: list[dict[str, Any]]) -> set[str]:
    """Bazada allaqachon bor havolalar (oxiridagi "/" farqisiz)."""
    return {
        str(p.get("source_url") or "").rstrip("/")
        for p in payloads
        if p.get("source_url")
    }


class ImportPressUseCase:
    def __init__(
        self,
        embedder: OllamaEmbedder,
        store: QdrantStore,
        fetch: Callable[[str], Awaitable[str]] = fetch_html,
        category: Callable[[str, str], Awaitable[str | None]] = named_category_key,
        today: date | None = None,
    ) -> None:
        self.embedder = embedder
        self.store = store
        self.fetch = fetch
        self.category = category
        self.today = today

    async def execute(self, max_pages: int, max_age_days: int) -> PressSummary:
        summary = PressSummary()
        exists = await self.store.exists()
        known = known_urls(await self.store.scroll_all_pages()) if exists else set()
        today = self.today or datetime.now().date()
        cutoff = today - timedelta(days=max_age_days)
        for section in SECTIONS:
            await self._section(section, known, cutoff, max_pages, summary)
        return summary

    async def _section(
        self,
        section: PressSection,
        known: set[str],
        cutoff: date,
        max_pages: int,
        summary: PressSummary,
    ) -> None:
        cat_key: str | None = None
        for page in range(1, max_pages + 1):
            url = section.list_url if page == 1 else f"{section.list_url}?PAGEN_1={page}"
            try:
                links = article_links(await self.fetch(url), section)
            except Exception as exc:  # noqa: BLE001 - bo'lim to'xtaydi, boshqasi davom etadi
                logger.warning("[Press] %s ochilmadi: %r", url, exc)
                summary.failed.append((url, type(exc).__name__))
                return
            fresh = [u for u in links if u.rstrip("/") not in known]
            # Sahifada yangi maqola yo'q (yoki sahifalar tugab, sayt oxirgi
            # sahifani qayta berdi) — qolgani allaqachon bazada
            if not fresh:
                return
            for link in fresh:
                summary.checked += 1
                known.add(link.rstrip("/"))
                try:
                    article = parse_article(await self.fetch(link), link)
                except Exception as exc:  # noqa: BLE001 - bitta maqola qolganini to'xtatmasin
                    logger.warning("[Press] %s ochilmadi: %r", link, exc)
                    summary.failed.append((link, type(exc).__name__))
                    continue
                if article.published and article.published < cutoff:
                    # Ro'yxat yangidan eskiga — bundan keyingilari ham eski
                    return
                if not article.text:
                    summary.failed.append((link, "empty"))
                    continue
                if cat_key is None:
                    cat_key = await self.category(section.category_key, section.category_name) or ""
                payload: dict[str, Any] = {"doc_type": PRESS_DOC_TYPE}
                if article.published:
                    payload["published"] = article.published.isoformat()
                if cat_key:
                    payload["category"] = [cat_key]
                title = record_title(section, article)
                try:
                    await UploadKnowledgeUseCase(
                        embedder=self.embedder, store=self.store
                    ).execute(
                        title=title,
                        text=record_text(section, article),
                        source_url=link,
                        extra_payload=payload,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("[Press] %s yozilmadi: %r", link, exc)
                    summary.failed.append((link, type(exc).__name__))
                    continue
                summary.added.append(title)
                logger.info("[Press] qo'shildi: %s", title)


class TriggerPressImportUseCase:
    """Yuklashni hoziroq navbatga qo'yadi (Celery worker bajaradi)."""

    def execute(self) -> None:
        from src.knowledge.tasks import import_press_center

        import_press_center.delay(manual=True)

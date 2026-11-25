"""Rasmiy saytning "Yangiliklar" va "E'lonlar" bo'limlarini bilim bazasiga yuklash.

Bo'lim sahifasida faqat sarlavha va sana bor — asosiy matn har maqolaning
ICHKI sahifasida. Shuning uchun:
  1) ro'yxat sahifasidan (kerak bo'lsa ?PAGEN_1=2) eng oxirgi N ta maqola
     havolasi olinadi (N = PRESS_KEEP_LATEST, standart 10);
  2) har maqola ochiladi: sarlavha (h1), sana (ko'rinadigan "10 Iyul 2026"),
     matn (.detail-text);
  3) maqola alohida yozuv bo'lib yoziladi: sarlavhada sana, turkumi
     "Yangiliklar" / "E'lonlar", doc_type=press.

Bazada har bo'limdan FAQAT oxirgi N tasi turadi: ro'yxatdan tushib qolgan
eski maqola o'chiriladi (eski yangiliklar xodimga kerak emas va qidiruvni
"ifloslaydi"). Sarlavhasi o'zgargan (masalan sana tuzatilgan) maqola qayta
yoziladi.

Matn saytdagidek saqlanadi (ba'zi maqolalar o'zbek YANGI alifbosida:
"işonç", "Özbekiston") — qidiruv ikkala yozuvni ham tushunadi
(qara: uzbek_script.from_new_alphabet)."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date
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
    # Sarlavhasi o'zgargani uchun qayta yozilganlar
    updated: list[str] = field(default_factory=list)
    # Oxirgi N tadan chiqib, bazadan o'chirilganlar
    removed: list[str] = field(default_factory=list)
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
    # Ko'rinadigan sana ("10 Iyul 2026") — haqiqiy e'lon sanasi. Meta
    # datePublished ishonchsiz: saytda u ko'pincha TAHRIR sanasi (10-iyul
    # yangiligida 2026-07-14, ba'zilarida hammasi oyning 1-kuni).
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
                pass
    meta = soup.find("meta", attrs={"itemprop": "datePublished"})
    if meta and meta.get("content"):
        try:
            return date.fromisoformat(str(meta["content"])[:10])
        except ValueError:
            pass
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


# Oxirgi N tani yig'ish uchun ko'pi bilan shuncha ro'yxat sahifasi
_MAX_LIST_PAGES = 3


def section_records(payloads: list[dict[str, Any]], section: PressSection) -> dict[str, set[str]]:
    """Bazadagi shu bo'lim yozuvlari: havola (oxiridagi "/" siz) -> sarlavhalar."""
    out: dict[str, set[str]] = {}
    for p in payloads:
        if p.get("doc_type") != PRESS_DOC_TYPE:
            continue
        url = str(p.get("source_url") or "")
        if urlparse(url).path.startswith(section.path):
            out.setdefault(url.rstrip("/"), set()).add(str(p.get("title") or ""))
    return out


class ImportPressUseCase:
    def __init__(
        self,
        embedder: OllamaEmbedder,
        store: QdrantStore,
        fetch: Callable[[str], Awaitable[str]] = fetch_html,
        category: Callable[[str, str], Awaitable[str | None]] = named_category_key,
    ) -> None:
        self.embedder = embedder
        self.store = store
        self.fetch = fetch
        self.category = category

    async def execute(self, keep: int) -> PressSummary:
        summary = PressSummary()
        payloads = await self.store.scroll_all_pages() if await self.store.exists() else []
        for section in SECTIONS:
            await self._section(section, payloads, keep, summary)
        return summary

    async def _latest_links(self, section: PressSection, keep: int) -> list[str]:
        """Bo'limdagi eng oxirgi `keep` ta maqola havolasi (sayt yangidan eskiga)."""
        links: list[str] = []
        for page in range(1, _MAX_LIST_PAGES + 1):
            url = section.list_url if page == 1 else f"{section.list_url}?PAGEN_1={page}"
            fresh = [u for u in article_links(await self.fetch(url), section) if u not in links]
            # Sahifalar tugadi (sayt oxirgi sahifani qayta berdi)
            if not fresh:
                break
            links += fresh
            if len(links) >= keep:
                break
        return links[:keep]

    async def _section(
        self,
        section: PressSection,
        payloads: list[dict[str, Any]],
        keep: int,
        summary: PressSummary,
    ) -> None:
        try:
            latest = await self._latest_links(section, keep)
        except Exception as exc:  # noqa: BLE001 - bo'lim to'xtaydi, boshqasi davom etadi
            logger.warning("[Press] %s ochilmadi: %r", section.list_url, exc)
            summary.failed.append((section.list_url, type(exc).__name__))
            return
        # Ro'yxat bo'sh — sayt tuzilmasi o'zgargan bo'lishi mumkin. Bunda
        # bazadagilarni o'chirib yubormaymiz.
        if not latest:
            summary.failed.append((section.list_url, "empty list"))
            return

        stored = section_records(payloads, section)
        cat_key: str | None = None
        for link in latest:
            summary.checked += 1
            try:
                article = parse_article(await self.fetch(link), link)
            except Exception as exc:  # noqa: BLE001 - bitta maqola qolganini to'xtatmasin
                logger.warning("[Press] %s ochilmadi: %r", link, exc)
                summary.failed.append((link, type(exc).__name__))
                continue
            if not article.text:
                summary.failed.append((link, "empty"))
                continue
            title = record_title(section, article)
            old = stored.get(link.rstrip("/"), set())
            if old == {title}:
                continue  # o'zgarmagan
            if cat_key is None:
                cat_key = await self.category(section.category_key, section.category_name) or ""
            payload: dict[str, Any] = {"doc_type": PRESS_DOC_TYPE}
            if article.published:
                payload["published"] = article.published.isoformat()
            if cat_key:
                payload["category"] = [cat_key]
            try:
                await UploadKnowledgeUseCase(
                    embedder=self.embedder, store=self.store
                ).execute(
                    title=title,
                    text=record_text(section, article),
                    source_url=link,
                    extra_payload=payload,
                )
            except Exception as exc:  # noqa: BLE001 - eski yozuv joyida qoladi
                logger.warning("[Press] %s yozilmadi: %r", link, exc)
                summary.failed.append((link, type(exc).__name__))
                continue
            # Eski sarlavhali yozuv (masalan noto'g'ri sana bilan) o'chadi
            for t in old - {title}:
                await self.store.delete_by_title(t)
            (summary.updated if old else summary.added).append(title)
            logger.info("[Press] %s: %s", "yangilandi" if old else "qo'shildi", title)

        # Oxirgi N tadan chiqib qolganlar bazadan o'chiriladi
        keep_urls = {u.rstrip("/") for u in latest}
        stale = sorted(t for url, ts in stored.items() if url not in keep_urls for t in ts)
        if stale:
            # Birinchi ishga tushishda yuzlab eski yozuv — bitta so'rov bilan
            await self.store.delete_by_titles(stale)
            summary.removed.extend(stale)


class TriggerPressImportUseCase:
    """Yuklashni hoziroq navbatga qo'yadi (Celery worker bajaradi)."""

    def execute(self) -> None:
        from src.knowledge.tasks import import_press_center

        import_press_center.delay(manual=True)

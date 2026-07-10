"""Fetch a web page and extract its clean main text.

trafilatura strips boilerplate (menus, header, footer, ads) and returns just
the readable article/content text — good for feeding into the RAG pipeline.
"""

import re

from bs4 import BeautifulSoup
import httpx
import trafilatura

from src.core.errors.exceptions import InfrastructureException
from src.main.config import config

# Sahifadagi fayl-yuklash / video vidjetlaridan qolgan "chalasoz" qatorlar —
# mazmunga aloqasi yo'q, faqat chalg'itadi. Bunday qatorlarni tashlab yuboramiz.
_NOISE_LINE_RE = re.compile(
    r"^(video|hujjatlar)$|^format:\s*\S+$|^havola:.*$",
    re.IGNORECASE,
)


def _strip_noise_lines(text: str) -> str:
    lines = text.split("\n")
    kept = [ln for ln in lines if not _NOISE_LINE_RE.match(ln.strip())]
    return "\n".join(kept)


# Brauzerga o'xshash User-Agent — ba'zi saytlar oddiy so'rovlarni bloklaydi
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    )
}


async def fetch_html(url: str, timeout: int = 30) -> str:
    # Alohida client: SSL tekshiruvini o'chiramiz (bank tarmog'i HTTPS'ni ushlaydi),
    # brauzer UA va redirect'larni yoqamiz. Agar bank tarmog'i tashqi HTTPS'ni
    # to'g'ridan-to'g'ri bloklasa, PROXY_URL orqali korporativ proxy ishlatiladi.
    proxy = config.scraping.PROXY_URL or None
    try:
        async with httpx.AsyncClient(
            verify=False,
            follow_redirects=True,
            headers=_HEADERS,
            timeout=timeout,
            proxy=proxy,
        ) as client:
            resp = await client.get(url)
    except httpx.HTTPError as exc:
        raise InfrastructureException(
            f"Sahifani olishda xatolik: {type(exc).__name__}: {exc!r}"
        ) from exc
    if resp.status_code != 200:
        raise InfrastructureException(f"Sahifa xatosi {resp.status_code}: {url}")
    return resp.text


# turonbank.uz'ga xos: mahsulot sahifalaridagi "asosiy ko'rsatkichlar" va
# "shartlar" qutilari label/qiymat juftligi ko'rinishida (masalan "Yillik
# stavka: 18%"), trafilatura bularni oddiy matn oqimi emasligi sabab
# tashlab yuboradi. Shu qutilarni alohida topib, matnga qo'shib qo'yamiz.
_KEY_FACT_SELECTORS = [
    # (qutini o'zi, label selector, qiymat selector) — natija "Label: Qiymat"
    (".heading-info__item", ".heading-info__label", ".heading-info__value"),
    (".conditions__row", ".conditions__label", ".conditions__value"),
]


def _extract_key_facts(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    facts: list[str] = []

    for item_sel, label_sel, value_sel in _KEY_FACT_SELECTORS:
        for item in soup.select(item_sel):
            label = item.select_one(label_sel)
            value = item.select_one(value_sel)
            if not label or not value:
                continue
            label_text = label.get_text(strip=True)
            value_text = value.get_text(strip=True)
            if not label_text or not value_text:
                continue
            facts.append(f"{label_text}: {value_text}")

    # Dublikatlarni olib tashlaymiz, tartibni saqlaymiz
    seen: set[str] = set()
    unique: list[str] = []
    for f in facts:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    return "\n".join(unique)


def extract_content(html: str, url: str) -> tuple[str, str]:
    """Return (title, clean_text). clean_text is '' if nothing extractable."""
    text = trafilatura.extract(html, url=url, favor_recall=True) or ""
    text = _strip_noise_lines(text)
    key_facts = _extract_key_facts(html)

    combined = text.strip()
    if key_facts:
        combined = f"{key_facts}\n\n{combined}" if combined else key_facts

    title = ""
    meta = trafilatura.extract_metadata(html)
    if meta and meta.title:
        title = str(meta.title)
    if not title:
        # URL oxirgi bo'lagidan zaxira sarlavha (masalan "humo-visa-kobeyjing-kartasi")
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        title = slug.replace("-", " ").strip() or url

    return title.strip(), combined.strip()

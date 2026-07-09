"""Fetch a web page and extract its clean main text.

trafilatura strips boilerplate (menus, header, footer, ads) and returns just
the readable article/content text — good for feeding into the RAG pipeline.
"""

import httpx
import trafilatura

from src.core.errors.exceptions import InfrastructureException


# Brauzerga o'xshash User-Agent — ba'zi saytlar oddiy so'rovlarni bloklaydi
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    )
}


async def fetch_html(url: str, timeout: int = 30) -> str:
    # Alohida client: SSL tekshiruvini o'chiramiz (bank tarmog'i HTTPS'ni ushlaydi),
    # brauzer UA va redirect'larni yoqamiz.
    try:
        async with httpx.AsyncClient(
            verify=False,
            follow_redirects=True,
            headers=_HEADERS,
            timeout=timeout,
        ) as client:
            resp = await client.get(url)
    except httpx.HTTPError as exc:
        raise InfrastructureException(
            f"Sahifani olishda xatolik: {type(exc).__name__}: {exc!r}"
        ) from exc
    if resp.status_code != 200:
        raise InfrastructureException(f"Sahifa xatosi {resp.status_code}: {url}")
    return resp.text


def extract_content(html: str, url: str) -> tuple[str, str]:
    """Return (title, clean_text). clean_text is '' if nothing extractable."""
    text = trafilatura.extract(html, url=url, favor_recall=True) or ""

    title = ""
    meta = trafilatura.extract_metadata(html)
    if meta and meta.title:
        title = str(meta.title)
    if not title:
        # URL oxirgi bo'lagidan zaxira sarlavha (masalan "humo-visa-kobeyjing-kartasi")
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        title = slug.replace("-", " ").strip() or url

    return title.strip(), text.strip()

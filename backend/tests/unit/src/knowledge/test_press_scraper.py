"""Sayt Yangiliklar / E'lonlar bo'limlarini bilim bazasiga yuklash."""

from datetime import date
from typing import Any

import pytest

from src.core.utils.uzbek_script import from_new_alphabet
from src.knowledge import press_scraper as ps
from src.knowledge.answer_helpers import _text_words
from src.knowledge.rescrape import scrape_targets

NEWS, ADVERTS = ps.SECTIONS


def _news_list(*slugs: str) -> str:
    cards = "".join(
        f'<div class="news"><a href="/uz/press_center/news/{s}/" class="news__image"></a>'
        f'<div class="news__date">22 Noy 2026</div>'
        f'<h3 class="news__title"><a href="/uz/press_center/news/{s}/">T</a></h3></div>'
        for s in slugs
    )
    return (
        '<a href="/uz/press_center/news/">Yangiliklar</a><a href="/ru/press_center/news/">ru</a>'
        '<a href="/uz/press_center/news/rss/">rss</a>'
        f"{cards}"
        '<a href="/uz/press_center/news/abc?PAGEN_1=2">2</a>'
    )


def _article(title: str, iso: str, body: str) -> str:
    return (
        f'<h1>{title}</h1><article><meta itemprop="datePublished" content="{iso}">'
        f'<div class="post-date"><span class="post-date__text">x</span></div>'
        f'<div class="post-content detail-text">{body}</div></article>'
    )


def test_article_links_only_articles_in_order() -> None:
    links = ps.article_links(_news_list("b-yangilik", "a-yangilik", "b-yangilik"), NEWS)
    assert links == [
        "https://turonbank.uz/uz/press_center/news/b-yangilik/",
        "https://turonbank.uz/uz/press_center/news/a-yangilik/",
    ]


def test_parse_article_date_text_and_table() -> None:
    html = _article(
        "21-noyabr kuni ishlaydigan markazlar",
        "2026-11-20",
        "Qadrli mijozlar<br>markazlar ro'yxati:<table><tr><th>№</th><th>BXM</th></tr>"
        "<tr><td>1</td><td>Xorazm</td></tr></table>",
    )
    a = ps.parse_article(html, "https://turonbank.uz/uz/press_center/adverts/x/")
    assert a.title == "21-noyabr kuni ishlaydigan markazlar"
    assert a.published == date(2026, 11, 20)
    assert "Qadrli mijozlar\nmarkazlar ro'yxati:" in a.text
    assert "1 | Xorazm" in a.text
    assert ps.record_title(ADVERTS, a) == "E'lon 20.11.2026: 21-noyabr kuni ishlaydigan markazlar"
    assert "E'lon qilingan sana: 20.11.2026" in ps.record_text(ADVERTS, a)


def test_date_fallback_from_text() -> None:
    html = '<h1>T</h1><div class="post-date__text">17 Okt 2025</div><div class="detail-text">x</div>'
    assert ps.parse_article(html, "u").published == date(2025, 10, 17)


def test_new_alphabet_matches_current_latin() -> None:
    assert from_new_alphabet("işonç, Özbekiston, boğliq") == "ishonch, O‘zbekiston, bog‘liq"
    assert {"ishonchi", "uchun"} <= _text_words("mijozlar işonçi uçun")
    assert _text_words("Boşqaruv") == _text_words("Boshqaruv")


def test_press_records_skipped_by_rescrape() -> None:
    groups = {
        "Yangilik 22.11.2026: X": [{"source_url": "https://turonbank.uz/n/", "doc_type": "press"}],
        "Kredit": [{"source_url": "https://turonbank.uz/k/"}],
    }
    assert scrape_targets(groups) == [("Kredit", "https://turonbank.uz/k/")]


class _Store:
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self.payloads = payloads

    async def exists(self) -> bool:
        return True

    async def scroll_all_pages(self) -> list[dict[str, Any]]:
        return self.payloads


def _run(monkeypatch: pytest.MonkeyPatch, pages: dict[str, str], known: list[str], max_age: int = 365):  # noqa: ANN202
    uploads: list[dict[str, Any]] = []
    fetched: list[str] = []

    class _Upload:
        def __init__(self, **_: Any) -> None:
            pass

        async def execute(self, **kw: Any) -> None:
            uploads.append(kw)

    async def fetch(url: str) -> str:
        fetched.append(url)
        return pages.get(url, "<html></html>")

    async def category(key: str, name: str) -> str:
        return f"cat-{key}"

    monkeypatch.setattr(ps, "UploadKnowledgeUseCase", _Upload)
    uc = ps.ImportPressUseCase(
        embedder=None,  # type: ignore[arg-type]
        store=_Store([{"source_url": u} for u in known]),  # type: ignore[arg-type]
        fetch=fetch,
        category=category,
        today=date(2026, 11, 25),
    )
    return uc, uploads, fetched


BASE = "https://turonbank.uz/uz/press_center/news/"


@pytest.mark.asyncio
async def test_only_new_articles_written_and_paging_stops(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = {
        BASE: _news_list("yangi", "eski"),
        BASE + "yangi/": _article("Yangi xabar", "2026-11-22", "Matn"),
    }
    uc, uploads, fetched = _run(monkeypatch, pages, known=[BASE + "eski"])
    summary = await uc.execute(max_pages=5, max_age_days=365)
    assert [u["title"] for u in uploads] == ["Yangilik 22.11.2026: Yangi xabar"]
    up = uploads[0]
    assert up["source_url"] == BASE + "yangi/"
    assert up["extra_payload"] == {"doc_type": "press", "published": "2026-11-22", "category": ["cat-news"]}
    # 2-sahifa: undagi maqolalar (yana o'sha "yangi"/"eski") ma'lum — to'xtadi
    assert summary.added == ["Yangilik 22.11.2026: Yangi xabar"]
    assert fetched.count(BASE + "?PAGEN_1=3") == 0


@pytest.mark.asyncio
async def test_old_articles_stop_the_section(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = {
        BASE: _news_list("bugun", "otgan-yil", "undan-eski"),
        BASE + "bugun/": _article("Bugun", "2026-11-20", "a"),
        BASE + "otgan-yil/": _article("O'tgan yil", "2025-01-01", "b"),
        BASE + "undan-eski/": _article("Eski", "2024-01-01", "c"),
    }
    uc, uploads, fetched = _run(monkeypatch, pages, known=[])
    await uc.execute(max_pages=5, max_age_days=365)
    assert [u["title"] for u in uploads] == ["Yangilik 20.11.2026: Bugun"]
    assert BASE + "undan-eski/" not in fetched

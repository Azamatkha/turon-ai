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


def test_visible_date_wins_over_meta() -> None:
    # Saytda meta datePublished — tahrir sanasi; ko'rinadigani haqiqiysi
    html = (
        '<h1>T</h1><meta itemprop="datePublished" content="2026-07-14">'
        '<div class="post-date__text">10 Iyul 2026</div><div class="detail-text">x</div>'
    )
    assert ps.parse_article(html, "u").published == date(2026, 7, 10)


class _Store:
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self.payloads = payloads
        self.deleted: list[str] = []

    async def exists(self) -> bool:
        return True

    async def scroll_all_pages(self) -> list[dict[str, Any]]:
        return self.payloads

    async def delete_by_title(self, title: str) -> None:
        self.deleted.append(title)

    async def delete_by_titles(self, titles: list[str]) -> None:
        self.deleted.extend(titles)


def _press(url: str, title: str) -> dict[str, Any]:
    return {"source_url": url, "title": title, "doc_type": "press"}


def _run(monkeypatch: pytest.MonkeyPatch, pages: dict[str, str], stored: list[dict[str, Any]]):  # noqa: ANN202
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
    store = _Store(stored)
    uc = ps.ImportPressUseCase(
        embedder=None,  # type: ignore[arg-type]
        store=store,  # type: ignore[arg-type]
        fetch=fetch,
        category=category,
    )
    return uc, uploads, fetched, store


BASE = "https://turonbank.uz/uz/press_center/news/"


@pytest.mark.asyncio
async def test_new_written_unchanged_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = {
        BASE: _news_list("yangi", "eski"),
        BASE + "yangi/": _article("Yangi xabar", "2026-11-22", "Matn"),
        BASE + "eski/": _article("Eski xabar", "2026-11-20", "Matn"),
    }
    uc, uploads, _, store = _run(
        monkeypatch, pages, [_press(BASE + "eski/", "Yangilik 20.11.2026: Eski xabar")]
    )
    summary = await uc.execute(keep=10)
    assert [u["title"] for u in uploads] == ["Yangilik 22.11.2026: Yangi xabar"]
    up = uploads[0]
    assert up["source_url"] == BASE + "yangi/"
    assert up["extra_payload"] == {"doc_type": "press", "published": "2026-11-22", "category": ["cat-news"]}
    assert summary.added == ["Yangilik 22.11.2026: Yangi xabar"]
    assert store.deleted == []


@pytest.mark.asyncio
async def test_only_latest_kept_older_removed(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = {
        BASE: _news_list("a", "b", "c"),
        BASE + "a/": _article("A", "2026-11-22", "x"),
        BASE + "b/": _article("B", "2026-11-21", "x"),
    }
    stored = [
        _press(BASE + "b/", "Yangilik 21.11.2026: B"),
        _press(BASE + "yozgi/", "Yangilik 01.07.2026: Yozgi"),
        # E'lonlar bo'limi yozuviga yangiliklar tegmaydi
        _press("https://turonbank.uz/uz/press_center/adverts/e/", "E'lon 20.11.2026: E"),
    ]
    uc, uploads, fetched, store = _run(monkeypatch, pages, stored)
    summary = await uc.execute(keep=2)
    assert [u["title"] for u in uploads] == ["Yangilik 22.11.2026: A"]
    assert BASE + "c/" not in fetched
    assert store.deleted == ["Yangilik 01.07.2026: Yozgi"]
    assert summary.removed == ["Yangilik 01.07.2026: Yozgi"]


@pytest.mark.asyncio
async def test_wrong_date_record_rewritten(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = {
        BASE: _news_list("a"),
        BASE + "a/": _article("A", "2026-07-10", "x"),
    }
    uc, uploads, _, store = _run(monkeypatch, pages, [_press(BASE + "a/", "Yangilik 01.07.2026: A")])
    summary = await uc.execute(keep=10)
    assert [u["title"] for u in uploads] == ["Yangilik 10.07.2026: A"]
    assert store.deleted == ["Yangilik 01.07.2026: A"]
    assert summary.updated == ["Yangilik 10.07.2026: A"]


@pytest.mark.asyncio
async def test_empty_list_deletes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    uc, uploads, _, store = _run(monkeypatch, {}, [_press(BASE + "a/", "Yangilik 22.11.2026: A")])
    summary = await uc.execute(keep=10)
    assert uploads == [] and store.deleted == []
    assert summary.failed

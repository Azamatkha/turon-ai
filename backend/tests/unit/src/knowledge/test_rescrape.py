from typing import Any

import pytest

from src.knowledge import rescrape as rs
from src.knowledge.chunking import chunk_text
from src.knowledge.rates_scraper import RATES_TITLE


def _doc(title: str, text: str, url: str = "", **extra: Any) -> list[dict[str, Any]]:
    """Hujjatni yuklashdagidek bo'laklab payload'larga aylantiradi."""
    return [
        {"title": title, "chunk_text": c, "chunk_index": i, "source_url": url, **extra}
        for i, c in enumerate(chunk_text(text))
    ]


def test_scrape_targets_skips_rates_employees_and_files() -> None:
    groups = rs.group_by_title(
        _doc("Omonat", "Omonat shartlari matni.", "https://bank.uz/omonat")
        + _doc(RATES_TITLE, "kurslar", "https://bank.uz/rates")
        + _doc("Xodimlar", "Ali Valiyev", "https://bank.uz/x", doc_type="employee")
        + _doc("PDF hujjat", "Ichki nizom matni.")
    )
    assert rs.scrape_targets(groups) == [("Omonat", "https://bank.uz/omonat")]


def test_content_changed_exact() -> None:
    text = "Kredit foizi 22%. Muddat 36 oy."
    stored = _doc("Kredit", text)
    assert not rs.content_changed(stored, text)
    assert rs.content_changed(stored, text.replace("22%", "21%"))


def test_find_duplicates_ignores_case_and_spaces() -> None:
    groups = rs.group_by_title(
        _doc("A", "Bir xil   matn")
        + _doc("B", "bir xil matn")
        + _doc("C", "Boshqa matn")
    )
    dups = rs.find_duplicates(groups)
    assert dups == {"A": ["B"], "B": ["A"]}


class _FakeStore:
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self.payloads = payloads

    async def exists(self) -> bool:
        return True

    async def scroll_all_pages(self) -> list[dict[str, Any]]:
        return list(self.payloads)


@pytest.mark.asyncio
async def test_rescrape_updates_only_changed(monkeypatch) -> None:
    store = _FakeStore(
        _doc("Same", "O'zgarmagan matn.", "https://bank.uz/same")
        + _doc("Changed", "Eski matn.", "https://bank.uz/changed")
        + _doc("Down", "Matn.", "https://bank.uz/down")
        + _doc("Empty", "Matn.", "https://bank.uz/empty")
    )
    pages = {
        "https://bank.uz/same": "O'zgarmagan matn.",
        "https://bank.uz/changed": "Yangi matn.",
        "https://bank.uz/empty": "",
    }

    async def fake_fetch(url: str) -> str:
        if url not in pages:
            raise ConnectionError("down")
        return url

    monkeypatch.setattr(rs, "fetch_html", fake_fetch)
    monkeypatch.setattr(rs, "extract_content", lambda html, url: ("t", pages[url]))

    updated: list[tuple[str, str]] = []

    class _FakeUpdate:
        def __init__(self, embedder: Any, store: Any) -> None:
            pass

        async def execute(self, old_title: str, title: str, text: str) -> None:
            updated.append((title, text))

    import src.knowledge.usecases as uc

    monkeypatch.setattr(uc, "UpdateKnowledgeUseCase", _FakeUpdate)

    summary = await rs.RescrapeKnowledgeUseCase(embedder=None, store=store).execute()  # type: ignore[arg-type]

    assert summary.checked == 4
    assert summary.unchanged == 1
    assert summary.changed == ["Changed"]
    assert updated == [("Changed", "Yangi matn.")]
    assert sorted(summary.failed) == [("Down", "ConnectionError"), ("Empty", "empty")]

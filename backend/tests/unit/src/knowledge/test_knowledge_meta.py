"""Admin qo'yadigan turkum va izoh: saqlash, ro'yxatda ko'rinishi, tahrirda
yo'qolmasligi. Bot katalogi FAQAT admin turkumiga tayanadi (avto yo'q)."""

from typing import Any

import pytest

from src.core.errors.exceptions import InstanceNotFoundException
from src.knowledge import categories as cat_mod
from src.knowledge.categories import make_def, match_categories
from src.knowledge.ingest_usecases import (
    ListKnowledgeUseCase,
    SetKnowledgeMetaUseCase,
    UpdateKnowledgeUseCase,
)


class _Store:
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self.payloads = payloads
        self.deleted: list[str] = []

    async def exists(self) -> bool:
        return True

    async def scroll_all_pages(self, page: int = 1000) -> list[dict[str, Any]]:
        return [dict(p) for p in self.payloads]

    async def search_by_field(self, field: str, value: str, limit: int = 40) -> list[dict[str, Any]]:
        return [p for p in self.payloads if p.get(field) == value][:limit]

    async def set_payload_by_title(self, title: str, payload: dict[str, Any]) -> None:
        for p in self.payloads:
            if p.get("title") == title:
                p.update(payload)

    async def delete_by_title(self, title: str) -> None:
        self.deleted.append(title)


def _doc(title: str, url: str = "", text: str = "matn", **extra: Any) -> dict[str, Any]:
    return {"title": title, "chunk_index": 0, "chunk_text": text, "source_url": url, **extra}


def test_default_categories_keep_old_keys() -> None:
    """Avval qo'lda qo'yilgan "credit"/"deposit"... kalitlari ishlayveradi."""
    keys = {c.key for c in cat_mod.DEFAULT_CATEGORIES}
    assert keys == {"credit", "deposit", "card", "transfer", "branch", "other"}


def test_match_prefers_specific_custom_category() -> None:
    cats = [*cat_mod.DEFAULT_CATEGORIES, make_def("c1", "Ipoteka", "ipoteka, uy krediti")]
    found = match_categories("Ipoteka kreditlari qanday", cats)
    assert found[0].name == "Ipoteka"
    assert "Kreditlar" in [c.name for c in found]


def test_custom_category_without_keywords_matches_by_name() -> None:
    cat = make_def("c2", "Biznes kreditlar", "")
    assert match_categories("biznes kreditlar ro'yxati", [cat]) == [cat]


@pytest.mark.asyncio
async def test_set_meta_and_list() -> None:
    store = _Store([_doc("Ichki tartib", text="umumiy qoidalar")])
    await SetKnowledgeMetaUseCase(store).execute("Ichki tartib", "credit", "  kredit bo'limi uchun ")  # type: ignore[arg-type]
    [item] = await ListKnowledgeUseCase(store).execute()  # type: ignore[arg-type]
    assert item.category == "credit"
    assert item.note == "kredit bo'limi uchun"

    # Olib tashlash — "Turkumsiz"
    await SetKnowledgeMetaUseCase(store).execute("Ichki tartib", None, "")  # type: ignore[arg-type]
    [item] = await ListKnowledgeUseCase(store).execute()  # type: ignore[arg-type]
    assert item.category == "" and item.note == ""


@pytest.mark.asyncio
async def test_set_meta_unknown_title() -> None:
    with pytest.raises(InstanceNotFoundException):
        await SetKnowledgeMetaUseCase(_Store([])).execute("Yo'q", "credit", None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_update_keeps_admin_meta() -> None:
    store = _Store([_doc("A", "https://x.uz/a", category="deposit", note="izoh", valid_until="2027-01-01")])
    url, kept = await UpdateKnowledgeUseCase(None, store)._existing_meta("A")  # type: ignore[arg-type]
    assert url == "https://x.uz/a"
    assert kept == {"category": "deposit", "note": "izoh", "valid_until": "2027-01-01"}


@pytest.mark.asyncio
async def test_list_hides_deleted_category() -> None:
    """Turkumi o'chirilgan hujjat ro'yxatda "Turkumsiz" ("")."""
    store = _Store([_doc("A", category="c-ochirilgan")])
    [item] = await ListKnowledgeUseCase(store).execute()  # type: ignore[arg-type]
    assert item.category == ""


@pytest.mark.asyncio
async def test_catalog_uses_only_manual_category() -> None:
    """Havolasi kreditlar bo'limida bo'lsa ham turkum FAQAT admin qo'ygani.
    Turkumsiz hujjat hech qaysi turkum ro'yxatiga tushmaydi."""
    from src.knowledge.usecases import AnswerQuestionUseCase

    uc = AnswerQuestionUseCase(embedder=None, store=None, ai_client=None)  # type: ignore[arg-type]
    points = [
        _doc("Aralash mahsulot", "https://turonbank.uz/uz/credits/x", category="deposit"),
        _doc("Avtokredit", "https://turonbank.uz/uz/credits/avto"),
    ]

    async def _scroll() -> list[dict[str, Any]]:
        return points

    uc._scroll_points = _scroll  # type: ignore[method-assign]
    groups = await uc._catalog_groups()
    assert groups["Omonatlar"] == ["Aralash mahsulot"]
    assert "Kreditlar" not in groups
    assert groups[cat_mod.UNCATEGORIZED_LABEL] == ["Avtokredit"]

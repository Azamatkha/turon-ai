"""Admin qo'yadigan turkum va izoh: saqlash, ro'yxatda ko'rinishi, tahrirda
yo'qolmasligi va bot katalogida avtomatikdan ustun turishi."""

from typing import Any

import pytest

from src.core.errors.exceptions import InstanceNotFoundException
from src.knowledge.answer_helpers import KB_CATEGORIES, category_key
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


def test_category_keys_match_labels() -> None:
    assert category_key("https://turonbank.uz/uz/private/credits/avto") == "credit"
    assert category_key("https://turonbank.uz/uz/private/deposits/meros") == "deposit"
    assert category_key("", "Meros omonati", "omonat foizi") == "deposit"
    assert set(KB_CATEGORIES) == {"credit", "deposit", "card", "transfer", "branch", "other"}


@pytest.mark.asyncio
async def test_set_meta_and_list() -> None:
    store = _Store([_doc("Ichki tartib", text="umumiy qoidalar")])
    await SetKnowledgeMetaUseCase(store).execute("Ichki tartib", "credit", "  kredit bo'limi uchun ")  # type: ignore[arg-type]
    [item] = await ListKnowledgeUseCase(store).execute()  # type: ignore[arg-type]
    assert item.category == "credit"
    assert item.note == "kredit bo'limi uchun"
    assert item.auto_category == "other"

    # Olib tashlash — bot yana o'zi aniqlaydi
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
async def test_catalog_prefers_manual_category() -> None:
    from src.knowledge.usecases import AnswerQuestionUseCase

    uc = AnswerQuestionUseCase(embedder=None, store=None, ai_client=None)  # type: ignore[arg-type]
    points = [
        # Havolasi kreditlar bo'limida, lekin admin "omonat" deb belgilagan
        _doc("Aralash mahsulot", "https://turonbank.uz/uz/credits/x", category="deposit"),
        _doc("Avtokredit", "https://turonbank.uz/uz/credits/avto"),
    ]

    async def _scroll() -> list[dict[str, Any]]:
        return points

    uc._scroll_points = _scroll  # type: ignore[method-assign]
    groups = await uc._catalog_groups()
    assert groups["Omonatlar"] == ["Aralash mahsulot"]
    assert groups["Kreditlar"] == ["Avtokredit"]

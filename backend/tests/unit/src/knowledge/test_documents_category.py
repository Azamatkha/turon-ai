"""PDF orqali yuklangan hujjat "Hujjatlar" turkumiga tushadi."""

import pytest

from src.knowledge import categories


@pytest.mark.asyncio
async def test_existing_admin_category_is_reused(monkeypatch: pytest.MonkeyPatch) -> None:
    # Admin o'zi "Hujjatlar" nomli turkum yaratgan — yangisi yaratilmaydi
    async def _cats() -> list[categories.CategoryDef]:
        return [*categories.DEFAULT_CATEGORIES, categories.make_def("c1234", "Hujjatlar", "")]

    async def _create() -> str:
        raise AssertionError("yaratilmasligi kerak edi")

    monkeypatch.setattr(categories, "kb_categories", _cats)
    monkeypatch.setattr(categories, "_create_documents_category", _create)
    assert await categories.documents_category_key() == "c1234"


@pytest.mark.asyncio
async def test_missing_category_is_created(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[bool] = []

    async def _create() -> str:
        created.append(True)
        return categories.DOCUMENTS_KEY

    monkeypatch.setattr(categories, "_create_documents_category", _create)
    assert await categories.documents_category_key() == categories.DOCUMENTS_KEY
    assert created == [True]


@pytest.mark.asyncio
async def test_failure_does_not_break_upload(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _create() -> str:
        raise RuntimeError("baza ishlamayapti")

    monkeypatch.setattr(categories, "_create_documents_category", _create)
    assert await categories.documents_category_key() is None

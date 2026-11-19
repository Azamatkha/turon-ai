"""Bilim bazasi turkumlarini boshqarish (admin) va hujjatlarga turkum qo'yish."""

import uuid

from fastapi import Depends

from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import (
    InstanceAlreadyExistsException,
    InstanceNotFoundException,
)
from src.core.vectorstore.qdrant_store import QdrantStore
from src.knowledge.categories import invalidate_categories, parse_keywords
from src.knowledge.models import KbCategory
from src.knowledge.schemas import KbCategoryIn, KbCategoryView

CATEGORY_NOT_FOUND = "Turkum topilmadi"
CATEGORY_EXISTS = "Bunday nomli turkum allaqachon bor"


def _to_view(c: KbCategory) -> KbCategoryView:
    return KbCategoryView(
        key=c.key,
        name=c.name,
        keywords=parse_keywords(c.keywords or ""),
        sort_order=c.sort_order,
    )


def _keywords_text(words: list[str]) -> str:
    return ", ".join(parse_keywords(",".join(words)))


class ListCategoriesUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self) -> list[KbCategoryView]:
        async with self.uow as uow:
            rows = await uow.kb_categories.list_ordered(uow.session)
            return [_to_view(c) for c in rows]


class CreateCategoryUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, data: KbCategoryIn) -> KbCategoryView:
        name = " ".join(data.name.split())
        async with self.uow as uow:
            rows = await uow.kb_categories.list_ordered(uow.session)
            if any(c.name.lower() == name.lower() for c in rows):
                raise InstanceAlreadyExistsException(CATEGORY_EXISTS)
            order = data.sort_order
            if order is None:
                order = await uow.kb_categories.max_sort_order(uow.session) + 10
            cat = await uow.kb_categories.create(
                uow.session,
                {
                    "key": f"c{uuid.uuid4().hex[:10]}",
                    "name": name,
                    "keywords": _keywords_text(data.keywords),
                    "sort_order": order,
                },
            )
            await uow.commit()
            view = _to_view(cat)
        invalidate_categories()
        return view


class UpdateCategoryUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, key: str, data: KbCategoryIn) -> KbCategoryView:
        name = " ".join(data.name.split())
        async with self.uow as uow:
            rows = await uow.kb_categories.list_ordered(uow.session)
            if any(c.name.lower() == name.lower() and c.key != key for c in rows):
                raise InstanceAlreadyExistsException(CATEGORY_EXISTS)
            values: dict[str, object] = {
                "name": name,
                "keywords": _keywords_text(data.keywords),
            }
            if data.sort_order is not None:
                values["sort_order"] = data.sort_order
            cat = await uow.kb_categories.update(uow.session, values, key=key)
            if cat is None:
                raise InstanceNotFoundException(CATEGORY_NOT_FOUND)
            await uow.commit()
            view = _to_view(cat)
        invalidate_categories()
        return view


class DeleteCategoryUseCase:
    """Turkumni o'chiradi. Unga qo'yilgan hujjatlar "Turkumsiz" bo'lib qoladi
    (payload'dagi kalit endi hech qaysi turkumga mos kelmaydi)."""

    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, key: str) -> None:
        async with self.uow as uow:
            cat = await uow.kb_categories.delete(uow.session, key=key)
            if cat is None:
                raise InstanceNotFoundException(CATEGORY_NOT_FOUND)
            await uow.commit()
        invalidate_categories()


async def ensure_category_exists(
    uow: ApplicationUnitOfWork[RepositoryProtocol], key: str | None
) -> None:
    """Hujjatga qo'yilayotgan turkum haqiqatan mavjudmi (None — olib tashlash)."""
    if not key:
        return
    async with uow as u:
        if await u.kb_categories.get_single(u.session, key=key) is None:
            raise InstanceNotFoundException(CATEGORY_NOT_FOUND)


class BulkSetCategoryUseCase:
    """Belgilangan hujjatlarga bitta turkum qo'yadi — faqat payload yangilanadi,
    vektorlar qayta hisoblanmaydi."""

    def __init__(
        self, uow: ApplicationUnitOfWork[RepositoryProtocol], store: QdrantStore
    ) -> None:
        self.uow = uow
        self.store = store

    async def execute(self, titles: list[str], category: str | None) -> int:
        await ensure_category_exists(self.uow, category)
        done = 0
        for title in dict.fromkeys(titles):
            await self.store.set_payload_by_title(title, {"category": category or None})
            done += 1
        return done


def get_list_categories_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> ListCategoriesUseCase:
    return ListCategoriesUseCase(uow=uow)


def get_create_category_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> CreateCategoryUseCase:
    return CreateCategoryUseCase(uow=uow)


def get_update_category_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> UpdateCategoryUseCase:
    return UpdateCategoryUseCase(uow=uow)


def get_delete_category_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> DeleteCategoryUseCase:
    return DeleteCategoryUseCase(uow=uow)

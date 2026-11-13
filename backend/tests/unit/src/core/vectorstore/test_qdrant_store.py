from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.core.vectorstore import qdrant_store as qs
from src.core.vectorstore.qdrant_store import QdrantStore


def _store(client: Any) -> QdrantStore:
    store = QdrantStore()
    store.client = client
    return store


@pytest.mark.asyncio
async def test_scroll_all_records_reads_every_page() -> None:
    pages = [
        ([SimpleNamespace(id=1, payload={"a": 1}), SimpleNamespace(id=2, payload=None)], "next"),
        ([SimpleNamespace(id=3, payload={"a": 3})], None),
    ]
    client = SimpleNamespace(
        collection_exists=AsyncMock(return_value=True),
        scroll=AsyncMock(side_effect=pages),
    )

    records = await _store(client).scroll_all_records(page=2)

    assert records == [(1, {"a": 1}), (2, {}), (3, {"a": 3})]
    assert client.scroll.await_count == 2
    assert client.scroll.await_args_list[1].kwargs["offset"] == "next"


@pytest.mark.asyncio
async def test_delete_stale_chunks_filters_title_and_tail() -> None:
    client = SimpleNamespace(
        collection_exists=AsyncMock(return_value=True), delete=AsyncMock()
    )

    await _store(client).delete_stale_chunks("Avtokredit", keep=3)

    flt = client.delete.await_args.kwargs["points_selector"]
    title_cond, index_cond = flt.must
    assert (title_cond.key, title_cond.match.value) == ("title", "Avtokredit")
    assert (index_cond.key, index_cond.range.gte) == ("chunk_index", 3)


@pytest.mark.asyncio
async def test_payload_indexes_created_once() -> None:
    client = SimpleNamespace(
        collection_exists=AsyncMock(return_value=True),
        create_payload_index=AsyncMock(),
    )
    store = _store(client)

    await store.ensure_payload_indexes()
    await store.ensure_payload_indexes()

    fields = [c.kwargs["field_name"] for c in client.create_payload_index.await_args_list]
    assert fields == [*qs._KEYWORD_INDEXES, *qs._INTEGER_INDEXES]


@pytest.mark.asyncio
async def test_payload_index_failure_is_not_fatal() -> None:
    client = SimpleNamespace(
        collection_exists=AsyncMock(side_effect=RuntimeError("qdrant o'chiq"))
    )
    store = _store(client)

    await store.ensure_payload_indexes()  # xato tashlamasligi kerak

    assert store._indexes_ready is False

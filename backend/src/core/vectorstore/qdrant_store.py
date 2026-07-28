"""Thin async wrapper around Qdrant for the knowledge collection.

Connection is lazy (the client only hits Qdrant on the first request),
so this is safe to construct at startup even if Qdrant is not up yet.
"""

import hashlib
from typing import Any
from uuid import UUID

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointIdsList,
    PointStruct,
    VectorParams,
)

from src.main.config import config


class QdrantStore:
    def __init__(self) -> None:
        self.client = AsyncQdrantClient(
            host=config.qdrant.QDRANT_HOST,
            port=config.qdrant.QDRANT_PORT,
        )
        self.collection = config.qdrant.QDRANT_COLLECTION

    async def ensure_collection(self, dim: int) -> None:
        """Create the collection (size=dim, cosine) if it does not exist yet."""
        if not await self.client.collection_exists(self.collection):
            await self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

    @staticmethod
    def _stable_id(payload: dict[str, Any]) -> str:
        """title + chunk_index'dan barqaror ID hosil qiladi — bir xil ma'lumot
        qayta yozilsa (masalan qayta scrape qilinganda), eskisi USTIGA yoziladi,
        dublikat point paydo bo'lmaydi."""
        key = f"{payload.get('title', '')}::{payload.get('chunk_index', 0)}"
        digest = hashlib.md5(key.encode("utf-8")).hexdigest()
        return str(UUID(digest))

    async def upsert(
        self,
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
    ) -> None:
        """Write vectors + their payloads as points (deterministic ids)."""
        points = [
            PointStruct(
                id=self._stable_id(payload), vector=vector, payload=payload
            )
            for vector, payload in zip(vectors, payloads, strict=True)
        ]
        await self.client.upsert(collection_name=self.collection, points=points)

    async def count(self) -> int:
        """Total number of points currently in the collection."""
        result = await self.client.count(collection_name=self.collection)
        return result.count

    async def exists(self) -> bool:
        return await self.client.collection_exists(self.collection)

    async def scroll_all(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Return the payloads of all points (up to `limit`), vectors omitted."""
        records, _ = await self.client.scroll(
            collection_name=self.collection,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return [dict(record.payload or {}) for record in records]

    async def scroll_by_field(
        self, key: str, value: str, page: int = 1000
    ) -> list[dict[str, Any]]:
        """Return payloads of ALL points whose payload[key] == value, paginating
        through every page (no silent truncation). `page` is the batch size."""
        if not await self.exists():
            return []
        flt = Filter(must=[FieldCondition(key=key, match=MatchValue(value=value))])
        out: list[dict[str, Any]] = []
        offset: Any = None
        while True:
            records, offset = await self.client.scroll(
                collection_name=self.collection,
                scroll_filter=flt,
                limit=page,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            out.extend(dict(r.payload or {}) for r in records)
            if offset is None:
                break
        return out

    async def scroll_all_records(
        self, limit: int = 5000
    ) -> list[tuple[Any, dict[str, Any]]]:
        """Return (point_id, payload) for all points — id o'chirish uchun kerak."""
        if not await self.exists():
            return []
        records, _ = await self.client.scroll(
            collection_name=self.collection,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return [(r.id, dict(r.payload or {})) for r in records]

    async def delete_ids(self, ids: list[Any]) -> None:
        """Delete points by their ids (payload-filtr indeksiga bog'liq emas)."""
        if not ids or not await self.exists():
            return
        await self.client.delete(
            collection_name=self.collection,
            points_selector=PointIdsList(points=ids),
        )

    async def search(
        self, query_vector: list[float], top_k: int = 4
    ) -> list[tuple[dict[str, Any], float]]:
        """Return the `top_k` most similar points as (payload, score) pairs."""
        if not await self.exists():
            return []
        result = await self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        )
        return [(dict(point.payload or {}), point.score) for point in result.points]

    async def delete_by_field(self, key: str, value: str) -> None:
        """Delete every point whose payload[key] == value."""
        if not await self.exists():
            return
        await self.client.delete(
            collection_name=self.collection,
            points_selector=Filter(
                must=[FieldCondition(key=key, match=MatchValue(value=value))]
            ),
        )

    async def search_by_field(
        self, key: str, value: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Return payloads of points whose payload[key] == value (exact filter,
        no vector search) — used for reverse lookups (e.g. IP -> employee)."""
        if not await self.exists():
            return []
        records, _ = await self.client.scroll(
            collection_name=self.collection,
            scroll_filter=Filter(
                must=[FieldCondition(key=key, match=MatchValue(value=value))]
            ),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return [dict(r.payload or {}) for r in records]

    async def delete_by_title(self, title: str) -> None:
        """Delete every point whose payload.title matches (one uploaded item)."""
        if not await self.exists():
            return
        await self.client.delete(
            collection_name=self.collection,
            points_selector=Filter(
                must=[FieldCondition(key="title", match=MatchValue(value=title))]
            ),
        )

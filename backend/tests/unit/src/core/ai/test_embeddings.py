import json

import httpx
import pytest

from src.core.ai.embeddings import OllamaEmbedder
from src.core.errors.exceptions import InfrastructureException


def _embedder(handler: httpx.MockTransport) -> OllamaEmbedder:
    embedder = OllamaEmbedder(http=httpx.AsyncClient(transport=handler))
    embedder.base_url = "http://ollama.test"  # .env.test'da manzil bo'sh
    return embedder


@pytest.mark.asyncio
async def test_embed_many_batches_and_keeps_order() -> None:
    calls: list[list[str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        texts = json.loads(request.content)["input"]
        calls.append(texts)
        # Javobni ATAYLAB teskari tartibda qaytaramiz — `index` bo'yicha tiklanishi kerak
        data = [
            {"index": i, "embedding": [float(t.removeprefix("t"))]}
            for i, t in enumerate(texts)
        ]
        return httpx.Response(200, json={"data": list(reversed(data))})

    embedder = _embedder(httpx.MockTransport(handler))
    texts = [f"t{i}" for i in range(OllamaEmbedder.BATCH_SIZE + 3)]

    vectors = await embedder.embed_many(texts)

    assert [len(c) for c in calls] == [OllamaEmbedder.BATCH_SIZE, 3]
    assert vectors == [[float(i)] for i in range(len(texts))]


@pytest.mark.asyncio
async def test_embed_single_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["input"] == "salom"
        return httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2]}]})

    assert await _embedder(httpx.MockTransport(handler)).embed("salom") == [0.1, 0.2]


@pytest.mark.asyncio
async def test_embed_many_rejects_short_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [1.0]}]})

    with pytest.raises(InfrastructureException):
        await _embedder(httpx.MockTransport(handler)).embed_many(["a", "b"])


@pytest.mark.asyncio
async def test_embed_many_empty_makes_no_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("so'rov yuborilmasligi kerak")

    assert await _embedder(httpx.MockTransport(handler)).embed_many([]) == []

"""Text -> vector embedding via an Ollama embedding model
(e.g. mxbai-embed-large) through the OpenAI-compatible /v1/embeddings endpoint.

Kept separate from the chat client (OllamaClient): chat *writes* text,
embedding *measures* text. Both live on the same Ollama server.
"""

from typing import Any

from fastapi import Depends
import httpx

from src.core.ai.clients.ollama import ollama_error_message
from src.core.errors.exceptions import InfrastructureException
from src.core.http.dependencies import get_http_client
from src.main.config import config


class OllamaEmbedder:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self.base_url = config.ai.OLLAMA_BASE_URL.rstrip("/")
        self.model = config.ai.EMBEDDING_MODEL
        self.timeout = config.ai.TIMEOUT_SECONDS
        self.http = http

    # Bitta so'rovda yuboriladigan matnlar soni (yuklashda ishlatiladi).
    BATCH_SIZE = 32

    async def _request(self, payload_input: str | list[str]) -> list[list[float]]:
        try:
            resp = await self.http.post(
                f"{self.base_url}/v1/embeddings",
                json={"model": self.model, "input": payload_input},
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise InfrastructureException(
                f"Embedding connection error: {type(exc).__name__} {exc}".rstrip()
            ) from exc

        if resp.status_code != 200:
            raise InfrastructureException(
                "Embedding: "
                + ollama_error_message(resp.status_code, resp.text, self.model)
            )

        data: dict[str, Any] = resp.json()
        try:
            items = sorted(data["data"], key=lambda d: d.get("index", 0))
            vectors: list[list[float]] = [item["embedding"] for item in items]
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise InfrastructureException(
                f"Unexpected embedding response: {str(data)[:200]}"
            ) from exc
        return vectors

    async def embed(self, text: str) -> list[float]:
        """Return the embedding vector for a single piece of text."""
        vectors = await self._request(text)
        if not vectors:
            raise InfrastructureException("Unexpected embedding response: empty")
        return vectors[0]

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Ko'p matnni BATCH qilib vektorga o'giradi (tartib saqlanadi).

        Yuklashda har bo'lak uchun alohida HTTP so'rov o'rniga BATCH_SIZE
        tadan yuboriladi — katta PDF/xodimlar ro'yxati ancha tez yoziladi."""
        out: list[list[float]] = []
        for start in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[start : start + self.BATCH_SIZE]
            vectors = await self._request(batch)
            if len(vectors) != len(batch):
                raise InfrastructureException(
                    f"Embedding: {len(batch)} ta matnga {len(vectors)} ta vektor qaytdi"
                )
            out.extend(vectors)
        return out


async def get_embedder(
    http: httpx.AsyncClient = Depends(get_http_client),
) -> OllamaEmbedder:
    return OllamaEmbedder(http=http)

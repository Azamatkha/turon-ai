"""Text -> vector embedding via an Ollama embedding model
(e.g. mxbai-embed-large) through the OpenAI-compatible /v1/embeddings endpoint.

Kept separate from the chat client (OllamaClient): chat *writes* text,
embedding *measures* text. Both live on the same Ollama server.
"""

from typing import Any

from fastapi import Depends
import httpx

from src.core.errors.exceptions import InfrastructureException
from src.core.http.dependencies import get_http_client
from src.main.config import config


class OllamaEmbedder:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self.base_url = config.ai.OLLAMA_BASE_URL.rstrip("/")
        self.model = config.ai.EMBEDDING_MODEL
        self.timeout = config.ai.TIMEOUT_SECONDS
        self.http = http

    async def embed(self, text: str) -> list[float]:
        """Return the embedding vector for a single piece of text."""
        try:
            resp = await self.http.post(
                f"{self.base_url}/v1/embeddings",
                json={"model": self.model, "input": text},
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise InfrastructureException(
                f"Embedding connection error: {exc}"
            ) from exc

        if resp.status_code != 200:
            raise InfrastructureException(
                f"Embedding error {resp.status_code}: {resp.text[:200]}"
            )

        data: dict[str, Any] = resp.json()
        try:
            vector: list[float] = data["data"][0]["embedding"]
        except (KeyError, IndexError, TypeError) as exc:
            raise InfrastructureException(
                f"Unexpected embedding response: {str(data)[:200]}"
            ) from exc
        return vector


async def get_embedder(
    http: httpx.AsyncClient = Depends(get_http_client),
) -> OllamaEmbedder:
    return OllamaEmbedder(http=http)

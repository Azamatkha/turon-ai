"""num_ctx: loyiha oynani o'zi majburlamaydi — serverdagi model oynasi ishlatiladi."""

from typing import Any

import httpx
import pytest

from src.core.ai.clients.ollama import OllamaClient


def _client(ps_models: list[dict[str, Any]] | None) -> OllamaClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if ps_models is None:
            return httpx.Response(500)
        return httpx.Response(200, json={"models": ps_models})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    # singleton dekoratorini chetlab o'tamiz — har testga toza obyekt
    client: OllamaClient = OllamaClient.__wrapped__(http)  # type: ignore[attr-defined]
    client.base_url = "http://ollama.test"
    client.model = "qwen3.5:122b"
    client.min_num_ctx = 16384
    client.num_ctx = 32768
    client.send_num_ctx = True
    client._ctx_cache = None
    return client


@pytest.mark.parametrize(
    ("models", "expected"),
    [
        # Boshqa loyiha 65k bilan yuklagan — aynan 65k yuboriladi (qayta yuklanmaydi)
        ([{"name": "qwen3.5:122b", "context_length": 65536}], 65536),
        # Model yuklanmagan — num_ctx YUBORILMAYDI (config'dagi 32768 emas)
        ([], None),
        ([{"name": "boshqa:7b", "context_length": 8192}], None),
        # Juda kichik oyna — faqat minimum so'raladi
        ([{"name": "qwen3.5:122b", "context_length": 4096}], 16384),
        # /api/ps ishlamadi — yuborilmaydi
        (None, None),
    ],
)
async def test_num_ctx_follows_loaded_model(
    models: list[dict[str, Any]] | None, expected: int | None
) -> None:
    client = _client(models)
    opts = await client._options(0.2, 100)
    assert opts.get("num_ctx") == expected
    assert opts["num_predict"] == 100


async def test_context_window_reports_loaded() -> None:
    assert await _client([{"model": "qwen3.5:122b", "context_length": 65536}]).context_window() == 65536
    assert await _client([]).context_window() is None


async def test_send_disabled_never_sends() -> None:
    client = _client([{"name": "qwen3.5:122b", "context_length": 65536}])
    client.send_num_ctx = False
    opts = await client._options(None, 10)
    assert "num_ctx" not in opts
    assert await client.context_window() == 65536

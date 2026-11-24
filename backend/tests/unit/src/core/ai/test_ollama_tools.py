"""Ollama tool-calling: `tools` yuboriladi, `tool_calls` o'qiladi."""

import json
from typing import Any

import httpx

from src.core.ai.clients.ollama import OllamaClient

TOOLS = [{"type": "function", "function": {"name": "search_knowledge", "parameters": {}}}]


def _client(reply: dict[str, Any], sent: list[dict[str, Any]]) -> OllamaClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/ps":
            return httpx.Response(200, json={"models": []})
        sent.append(json.loads(request.content))
        return httpx.Response(200, json=reply)

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client: OllamaClient = OllamaClient.__wrapped__(http)  # type: ignore[attr-defined]
    client.base_url = "http://ollama.test"
    client.model = "qwen3.5:122b"
    client._ctx_cache = None
    return client


async def test_tool_calls_parsed_and_tools_sent() -> None:
    sent: list[dict[str, Any]] = []
    reply = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "search_knowledge", "arguments": {"query": "mukofot"}}},
                # Satr ko'rinishidagi argument ham o'qiladi
                {"function": {"name": "calculate_loan", "arguments": '{"amount": 100}'}},
                # Buzuq argument — bo'sh lug'at
                {"function": {"name": "get_exchange_rates", "arguments": "{buzuq"}},
                {"function": {"name": ""}},
            ],
        },
        "prompt_eval_count": 50,
        "eval_count": 7,
        "done_reason": "stop",
    }
    turn = await _client(reply, sent).chat_tools(
        [{"role": "user", "content": "salom"}], TOOLS, max_tokens=256
    )
    assert sent[0]["tools"] == TOOLS
    assert sent[0]["think"] is False
    assert [c.name for c in turn.tool_calls] == [
        "search_knowledge", "calculate_loan", "get_exchange_rates",
    ]
    assert turn.tool_calls[0].arguments == {"query": "mukofot"}
    assert turn.tool_calls[1].arguments == {"amount": 100}
    assert turn.tool_calls[2].arguments == {}
    assert turn.message["role"] == "assistant"
    assert turn.completion_tokens == 7


async def test_plain_text_reply() -> None:
    sent: list[dict[str, Any]] = []
    turn = await _client({"message": {"content": "Salom!"}}, sent).chat_tools(
        [{"role": "user", "content": "salom"}], TOOLS, max_tokens=64
    )
    assert turn.content == "Salom!"
    assert turn.tool_calls == []


async def test_plain_calls_send_no_tools() -> None:
    sent: list[dict[str, Any]] = []
    await _client({"message": {"content": "x"}}, sent).generate_text("q", max_tokens=8)
    assert "tools" not in sent[0]

"""AGENT_TOOLS_ENABLED: agent router'dan keyin ishlaydi, xatoda eski yo'l."""

from typing import Any

import pytest

from src.core.ai.schemas import ToolCall, ToolTurn
from src.knowledge.prompts import HARMFUL_REPLY
from src.knowledge.router import Intent, Route
from src.knowledge.usecases import AnswerQuestionUseCase
from src.main.config import config


class _AI:
    def __init__(self, turns: list[ToolTurn | Exception]) -> None:
        self.turns = turns
        self.tool_calls = 0

    async def chat_tools(self, messages: Any, tools: Any, **_: Any) -> ToolTurn:
        self.tool_calls += 1
        turn = self.turns.pop(0)
        if isinstance(turn, Exception):
            raise turn
        return turn

    async def stream_generate(self, *a: Any, **kw: Any) -> Any:
        # Eski yo'lning yakuniy javobi
        yield {"type": "delta", "text": "eski yo'l javobi"}
        yield {"type": "done", "completion_tokens": 3, "finish_reason": "stop"}


def _uc(monkeypatch: pytest.MonkeyPatch, ai: _AI, intent: Intent, enabled: bool = True) -> AnswerQuestionUseCase:
    monkeypatch.setattr(config.ai, "AGENT_TOOLS_ENABLED", enabled)
    monkeypatch.setattr(config.ai, "ANSWER_VERIFY", False)
    uc = AnswerQuestionUseCase(embedder=None, store=None, ai_client=ai)  # type: ignore[arg-type]

    async def no_hits(*a: Any, **kw: Any) -> list:
        return []

    async def classify(question: str, history: Any = None) -> Route:
        return Route(intent=intent, search_query=question)

    monkeypatch.setattr(uc, "_directory_hits", no_hits)
    monkeypatch.setattr(uc.router, "classify", classify)
    return uc


async def _events(uc: AnswerQuestionUseCase, q: str) -> list[dict[str, Any]]:
    return [e async for e in uc.execute_stream(q)]


def _text(events: list[dict[str, Any]]) -> str:
    return "".join(e.get("text", "") for e in events if e["type"] == "delta")


async def test_agent_answers_with_calculator(monkeypatch: pytest.MonkeyPatch) -> None:
    ai = _AI([
        ToolTurn(
            content="",
            tool_calls=[ToolCall(name="calculate_deposit", arguments={"amount": 50_000_000, "rate": 20, "months": 12})],
            message={"role": "assistant", "content": ""},
        ),
        ToolTurn(content="12 oyda foyda 10 000 000 so'm bo'ladi."),
    ])
    uc = _uc(monkeypatch, ai, Intent.PRODUCT)
    events = await _events(uc, "50 mln 12 oyga 20% omonat qancha foyda beradi")
    assert _text(events) == "12 oyda foyda 10 000 000 so'm bo'ladi."
    assert {"type": "status", "step": "calc"} in events
    assert uc.last_tools == ["calculate_deposit"]
    # Hisob natijasi keshlanmasin
    assert uc.last_intent == "calc"


async def test_flag_off_keeps_old_path(monkeypatch: pytest.MonkeyPatch) -> None:
    ai = _AI([])
    uc = _uc(monkeypatch, ai, Intent.CONCEPT, enabled=False)
    monkeypatch.setattr(uc, "_catalog_title_match", _no_title)
    events = await _events(uc, "annuitet nima")
    assert ai.tool_calls == 0
    assert "eski yo'l javobi" in _text(events)
    assert uc.last_tools == []


async def test_agent_error_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    ai = _AI([NotImplementedError()])
    uc = _uc(monkeypatch, ai, Intent.CONCEPT)
    monkeypatch.setattr(uc, "_catalog_title_match", _no_title)
    events = await _events(uc, "annuitet nima")
    assert ai.tool_calls == 1
    assert "eski yo'l javobi" in _text(events)


async def test_harmful_still_refused_before_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    ai = _AI([])
    uc = _uc(monkeypatch, ai, Intent.HARMFUL)
    events = await _events(uc, "xavfli savol")
    assert _text(events) == HARMFUL_REPLY
    assert ai.tool_calls == 0


async def _no_title(q: str) -> tuple[None, list[str]]:
    return None, []

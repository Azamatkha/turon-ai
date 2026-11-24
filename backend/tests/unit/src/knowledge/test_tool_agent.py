"""Tool-calling agenti sikli — soxta AI mijozi bilan."""

from typing import Any

from src.core.ai.schemas import ToolCall, ToolTurn
from src.knowledge import agent_tools
from src.knowledge.agent import ToolAgent
from src.knowledge.agent_tools import ToolContext, ToolResult


class _AI:
    """Navbatdagi ToolTurn'larni qaytaradi va yuborilgan xabarlarni yozib boradi."""

    def __init__(self, turns: list[ToolTurn | Exception]) -> None:
        self.turns = turns
        self.calls: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]] = []

    async def chat_tools(self, messages, tools, **_: Any) -> ToolTurn:  # noqa: ANN001
        self.calls.append(([dict(m) for m in messages], tools))
        turn = self.turns.pop(0)
        if isinstance(turn, Exception):
            raise turn
        return turn


def _call(name: str, **args: Any) -> ToolTurn:
    return ToolTurn(
        content="",
        tool_calls=[ToolCall(name=name, arguments=args)],
        message={"role": "assistant", "content": ""},
        completion_tokens=5,
    )


def _calls(*pairs: tuple[str, dict[str, Any]]) -> ToolTurn:
    return ToolTurn(
        content="",
        tool_calls=[ToolCall(name=n, arguments=a) for n, a in pairs],
        message={"role": "assistant", "content": ""},
    )


def _text(t: str) -> ToolTurn:
    return ToolTurn(content=t, completion_tokens=10)


def _agent(ai: _AI) -> ToolAgent:
    return ToolAgent(
        ai,  # type: ignore[arg-type]
        ToolContext(uc=None),  # type: ignore[arg-type]
        system_prompt="SYS",
        max_tokens=100,
        temperature=0.2,
    )


async def _run(agent: ToolAgent, msg: str = "savol") -> list[dict[str, Any]]:
    return [ev async for ev in agent.run(msg)]


def _fake_tools(monkeypatch, results: dict[str, ToolResult]) -> list[tuple[str, dict]]:  # noqa: ANN001
    seen: list[tuple[str, dict]] = []

    async def fake(ctx: ToolContext, name: str, args: dict[str, Any]) -> ToolResult:
        seen.append((name, args))
        return results[name]

    monkeypatch.setattr("src.knowledge.agent.run_tool", fake)
    return seen


async def test_one_tool_then_answer(monkeypatch) -> None:  # noqa: ANN001
    seen = _fake_tools(monkeypatch, {
        "search_knowledge": ToolResult(
            text="[Mukofotlash]\n100 mln", results=[({"title": "Mukofotlash"}, 0.9)]
        ),
    })
    ai = _AI([_call("search_knowledge", query="mukofot"), _text("Javob: 100 mln")])
    agent = _agent(ai)
    events = await _run(agent)
    assert events == [{"type": "status", "step": "search"}]
    assert seen == [("search_knowledge", {"query": "mukofot"})]
    a = agent.answer
    assert a is not None and a.text == "Javob: 100 mln"
    assert a.tools == ["search_knowledge"]
    assert [s.title for s in a.sources] == ["Mukofotlash"]
    assert "100 mln" in a.context and not a.verbatim and not a.no_info
    assert a.tokens == 15
    # Asbob natijasi modelga role=tool bo'lib qaytdi
    last_msgs = ai.calls[1][0]
    assert last_msgs[-1] == {"role": "tool", "tool_name": "search_knowledge", "content": "[Mukofotlash]\n100 mln"}


async def test_two_tools_in_one_question(monkeypatch) -> None:  # noqa: ANN001
    _fake_tools(monkeypatch, {
        "search_knowledge": ToolResult(text="Omonat 20%"),
        "calculate_deposit": ToolResult(text="Foyda: 10 000 000 so'm", status="calc"),
    })
    ai = _AI([
        _call("search_knowledge", query="omonat foizi"),
        _call("calculate_deposit", amount=50_000_000, rate=20, months=12),
        _text("20%, foyda 10 mln"),
    ])
    agent = _agent(ai)
    events = await _run(agent)
    assert [e["step"] for e in events] == ["search", "calc"]
    assert agent.answer is not None
    assert agent.answer.tools == ["search_knowledge", "calculate_deposit"]


async def test_no_tool_answer() -> None:
    agent = _agent(_AI([_text("Salom! Qanday yordam bera olaman?")]))
    assert await _run(agent) == []
    assert agent.answer is not None and agent.answer.tools == []


async def test_verbatim_returned_without_second_model_call(monkeypatch) -> None:  # noqa: ANN001
    _fake_tools(monkeypatch, {
        "find_employee": ToolResult(text="Karimov — 2206", verbatim="Karimov — 2206", status="employees"),
    })
    ai = _AI([_call("find_employee", query="Karimov")])
    agent = _agent(ai)
    await _run(agent)
    assert agent.answer is not None and agent.answer.verbatim
    assert agent.answer.text == "Karimov — 2206"
    assert len(ai.calls) == 1


async def test_mixed_verbatim_goes_back_to_model(monkeypatch) -> None:  # noqa: ANN001
    _fake_tools(monkeypatch, {
        "find_employee": ToolResult(text="Karimov", verbatim="Karimov", status="employees"),
        "search_knowledge": ToolResult(text="qoida"),
    })
    ai = _AI([
        _calls(("find_employee", {"query": "k"}), ("search_knowledge", {"query": "q"})),
        _text("ikkalasi"),
    ])
    agent = _agent(ai)
    await _run(agent)
    assert agent.answer is not None and agent.answer.text == "ikkalasi"
    assert not agent.answer.verbatim


async def test_error_falls_back_to_old_path() -> None:
    agent = _agent(_AI([NotImplementedError()]))
    await _run(agent)
    assert agent.answer is None


async def test_empty_reply_falls_back() -> None:
    agent = _agent(_AI([_text("   ")]))
    await _run(agent)
    assert agent.answer is None


async def test_step_limit_forces_answer_without_tools(monkeypatch) -> None:  # noqa: ANN001
    _fake_tools(monkeypatch, {"search_knowledge": ToolResult(text="NOT FOUND: x")})
    ai = _AI([_call("search_knowledge", query=str(i)) for i in range(3)] + [_text("topilmadi")])
    agent = _agent(ai)
    await _run(agent)
    assert ai.calls[-1][1] == []  # oxirgi qadamda asbob berilmadi
    assert ai.calls[0][1] == agent_tools.TOOL_SPECS
    assert agent.answer is not None and agent.answer.no_info


async def test_tool_crash_does_not_break_answer(monkeypatch) -> None:  # noqa: ANN001
    async def boom(ctx, name, args):  # noqa: ANN001, ANN202
        raise RuntimeError("qdrant yiqildi")

    monkeypatch.setattr("src.knowledge.agent.run_tool", boom)
    ai = _AI([_call("search_knowledge", query="x"), _text("hozir javob bera olmayman")])
    agent = _agent(ai)
    await _run(agent)
    assert agent.answer is not None and agent.answer.no_info

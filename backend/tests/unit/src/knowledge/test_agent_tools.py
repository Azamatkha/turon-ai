"""Tool-calling asboblari: mavjud kodga yupqa qobiq."""

from typing import Any

import pytest

from src.knowledge import agent_tools as t


class _UC:
    """AnswerQuestionUseCase o'rnini bosuvchi soxta obyekt."""

    MIN_SCORE = 0.5

    def __init__(self) -> None:
        self.search_results: list[tuple[dict[str, Any], float]] = []
        self.lexical: list[tuple[dict[str, Any], float]] = []
        self.dir_hits: list[dict[str, Any]] = []
        self.route: tuple[str, list[dict[str, Any]]] | None = None
        self._emp_note: str | None = None

    async def _search_chunks(self, q: str, sq: str):  # noqa: ANN202
        return self.search_results, self.lexical

    async def _broad_category_reply(self, q: str, cyr: bool):  # noqa: ANN202
        return ("1. Mikroqarz\n2. Avtokredit", None) if "kredit" in q else (None, None)

    async def _directory_hits(self, q: str) -> list[dict[str, Any]]:
        return self.dir_hits

    async def _employee_route(self, q: str):  # noqa: ANN202
        return self.route


def _ctx(uc: _UC) -> t.ToolContext:
    return t.ToolContext(uc=uc)  # type: ignore[arg-type]


async def test_search_returns_blocks_and_sources() -> None:
    uc = _UC()
    uc.search_results = [({"title": "Mukofotlash tartibi", "chunk_text": "100 mln"}, 0.8)]
    r = await t.run_tool(_ctx(uc), "search_knowledge", {"query": "mukofot"})
    assert "[Mukofotlash tartibi]" in r.text and "100 mln" in r.text
    assert r.results and r.verbatim is None


async def test_search_low_score_is_not_found() -> None:
    uc = _UC()
    uc.search_results = [({"title": "X", "chunk_text": "y"}, 0.1)]
    r = await t.run_tool(_ctx(uc), "search_knowledge", {"query": "nimadir"})
    assert r.text.startswith("NOT FOUND")


async def test_list_products_is_verbatim() -> None:
    r = await t.run_tool(_ctx(_UC()), "list_products", {"category": "kreditlar"})
    assert r.verbatim == "1. Mikroqarz\n2. Avtokredit"


async def test_employee_found_is_verbatim_and_not_found_is_text() -> None:
    uc = _UC()
    r = await t.run_tool(_ctx(uc), "find_employee", {"query": "Karimov"})
    assert r.verbatim is None and r.text.startswith("NOT FOUND")
    uc.dir_hits = [{"fish": "Karimov Anvar", "ip": "2206", "phone": ""}]
    r = await t.run_tool(_ctx(uc), "find_employee", {"query": "Karimov"})
    assert r.verbatim and "Karimov Anvar" in r.verbatim
    assert r.status == "employees"


async def test_loan_numbers_come_from_calculator() -> None:
    r = await t.run_tool(
        _ctx(_UC()),
        "calculate_loan",
        {"amount": 12_000_000, "rate": 0, "months": 12, "method": "annuity"},
    )
    assert "Oylik to'lov: 1 000 000 so'm" in r.text
    assert r.status == "calc"


async def test_mortgage_uses_price_minus_down_payment() -> None:
    r = await t.run_tool(
        _ctx(_UC()),
        "calculate_loan",
        {"price": 300_000_000, "down_payment": 60_000_000, "rate": 18, "months": 180},
    )
    assert "Kredit summasi: 240 000 000 so'm" in r.text


async def test_deposit() -> None:
    r = await t.run_tool(
        _ctx(_UC()), "calculate_deposit", {"amount": "50 000 000", "rate": 20, "months": 12}
    )
    assert "Foyda: 10 000 000 so'm" in r.text


@pytest.mark.parametrize(
    ("name", "args"),
    [
        ("calculate_loan", {"rate": 20, "months": 12}),
        ("calculate_loan", {"amount": 100, "rate": 20, "months": 999}),
        ("calculate_deposit", {"amount": 100, "rate": "abc", "months": 12}),
        ("search_knowledge", {}),
        ("no_such_tool", {}),
    ],
)
async def test_bad_args_return_error_text(name: str, args: dict[str, Any]) -> None:
    r = await t.run_tool(_ctx(_UC()), name, args)
    assert r.text.startswith("ERROR")


def test_specs_match_handlers() -> None:
    names = [s["function"]["name"] for s in t.TOOL_SPECS]
    assert sorted(names) == sorted(t.HANDLERS)

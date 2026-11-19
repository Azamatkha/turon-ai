"""Xodim ro'yxatidan keyingi davom savoli.

"Сирдарё БХМ ички рақамлари" -> 15 xodim -> "рахбари керак". Ilgari ikkinchi
savol alohida qidirilib, boshqa filial xodimlari olinar va model "ma'lumot
yo'q" derdi — ro'yxatda "Rahbar o'rinbosari" bo'lsa ham."""

from typing import Any

import pytest

from src.core.utils.uzbek_script import to_cyrillic
from src.knowledge import usecases as uc_mod
from src.knowledge.answer_helpers import (
    _employee_list_question,
    _format_employee_answer,
    _refine_employee_list,
)
from src.knowledge.schemas import ChatTurn
from src.knowledge.usecases import AnswerQuestionUseCase


def _emp(fish: str, dept: str, pos: str, ip: str = "") -> dict[str, Any]:
    return {"fish": fish, "department": dept, "division": "", "position": pos, "ip": ip, "phone": ""}


DEPUTY = _emp("Qo'ziboyev Ilhom Abduazizovich", "Sirdaryo BXM", "Rahbar o'rinbosari", "4601")
HR = _emp("Rizoxodjayeva Maftuna", "Sirdaryo BXM", "HR xodimi")
IT = _emp("Popov Rinat", "Axborot texnologiyalari departamenti", "Bosh mutaxassis (Sirdaryo BXM bo'yicha)")
COMPL = _emp("Karimov Avazbek", "Komplaens nazorat departamenti", "Komplaens ofitser (Sirdaryo BXM bo'yicha)", "4630")
LIST = [DEPUTY, HR, IT, COMPL]


def _history(answer: str) -> list[ChatTurn]:
    return [
        ChatTurn(role="user", content="Сирдарё БХМ ички рақамлари"),
        ChatTurn(role="assistant", content=answer),
    ]


@pytest.mark.parametrize(
    "question,expected",
    [
        ("рахбари керак", [DEPUTY]),
        ("rahbarining raqami", [DEPUTY]),
        ("2", [HR]),
        ("komplaens", [COMPL]),
        ("IT dagisi", None),  # "dagisi" hech kimda yo'q -> odatdagi yo'l
        ("Ilhom", [DEPUTY]),
        ("99", None),
        ("kredit foizi qancha bo'ladi endi aytib ber", None),  # yangi savol
    ],
)
def test_refine(question: str, expected: list[dict[str, Any]] | None) -> None:
    assert _refine_employee_list(LIST, question) == expected


def test_list_question_detected_in_cyrillic_answer() -> None:
    answer = to_cyrillic(_format_employee_answer(LIST))
    assert _employee_list_question(_history(answer)) == "Сирдарё БХМ ички рақамлари"


def test_non_employee_answer_is_not_a_list() -> None:
    assert _employee_list_question(_history("Kredit foizi 24%.")) is None


@pytest.mark.asyncio
async def test_followup_answers_from_previous_list(monkeypatch: pytest.MonkeyPatch) -> None:
    uc = AnswerQuestionUseCase(embedder=None, store=None, ai_client=None)  # type: ignore[arg-type]
    asked: list[str] = []

    async def no_directory(q: str) -> list[dict[str, Any]]:
        return []

    async def route(q: str) -> tuple[str, list[dict[str, Any]]]:
        asked.append(q)
        return "answer", LIST

    monkeypatch.setattr(uc, "_directory_hits", no_directory)
    monkeypatch.setattr(uc, "_employee_route", route)
    history = _history(to_cyrillic(_format_employee_answer(LIST)))
    assert await uc._employee_followup("рахбари керак", history) == [DEPUTY]
    # Ro'yxat oldingi savol (lotinga o'girilgan) bilan qayta tuziladi
    assert asked == ["Sirdaryo BXM ichki raqamlari"]


@pytest.mark.parametrize("latin", ["yo'q", "yo‘q", "IP: yo'q"])
def test_yoq_to_cyrillic(latin: str) -> None:
    """"yo'q" — "й" + "ў" + "қ"; ilgari "ёъқ" bo'lib chiqardi."""
    assert to_cyrillic(latin).endswith("йўқ")
    assert uc_mod.to_cyrillic("Yoshlar") == "Ёшлар"  # oddiy "yo" o'zgarmagan

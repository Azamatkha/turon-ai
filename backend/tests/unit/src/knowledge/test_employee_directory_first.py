"""Xodim qidiruvi: avval users raqamlar ro'yxati, keyin vektor baza.
Apostrofli so'zlar ("o'zbekiston") ismga tasodifan mos kelmasligi."""

from typing import Any

import pytest

from src.knowledge import usecases as uc_mod
from src.knowledge.usecases import AnswerQuestionUseCase, _match_employees

VEC_EMP = {
    "doc_type": "employee",
    "fish": "Abrorov Navro‘zbek Mustafaxan o‘g‘li",
    "department": "Moliyaviy hisobotlar departamenti",
    "division": "",
    "position": "Bosh menejer",
    "ip": "2402",
    "phone": "+998(93) 638 04 01",
}
USER_EMP = {
    "fish": "Abrorov Navro'zbek",
    "department": "Moliyaviy hisobotlar departamenti",
    "division": "",
    "position": "Bosh menejer",
    "ip": "2410",
    "phone": "",
}


def test_apostrophe_word_does_not_match_name() -> None:
    q = "o'zbekiston respublikasi konstitutsiyasi"
    assert _match_employees([VEC_EMP], q) == []


def test_apostrophe_name_still_matches() -> None:
    assert _match_employees([VEC_EMP], "navro'zbekning ip raqami") == [VEC_EMP]


def _use_case(monkeypatch: pytest.MonkeyPatch, users: list[dict[str, Any]]) -> AnswerQuestionUseCase:
    uc = AnswerQuestionUseCase(embedder=None, store=None, ai_client=None)  # type: ignore[arg-type]

    async def fake_users() -> list[dict[str, Any]]:
        return users

    async def fake_points() -> list[dict[str, Any]]:
        return [VEC_EMP]

    async def no_ip(q: str) -> list[dict[str, Any]]:
        return []

    monkeypatch.setattr(uc_mod, "users_with_ip", fake_users)
    monkeypatch.setattr(uc, "_scroll_points", fake_points)
    monkeypatch.setattr(uc, "_lookup_by_ip_field", no_ip)
    return uc


@pytest.mark.asyncio
async def test_users_list_wins_over_vector(monkeypatch: pytest.MonkeyPatch) -> None:
    uc = _use_case(monkeypatch, [USER_EMP])
    assert await uc._employee_route("abrorov ip raqami") == ("answer", [USER_EMP])


@pytest.mark.asyncio
async def test_users_number_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    uc = _use_case(monkeypatch, [USER_EMP])
    assert await uc._employee_route("2410") == ("answer", [USER_EMP])


@pytest.mark.asyncio
async def test_falls_back_to_vector(monkeypatch: pytest.MonkeyPatch) -> None:
    uc = _use_case(monkeypatch, [])
    assert await uc._employee_route("abrorov ip raqami") == ("answer", [VEC_EMP])

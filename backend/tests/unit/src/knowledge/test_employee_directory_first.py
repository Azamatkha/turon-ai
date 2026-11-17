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
    """Bir odam ikkala manbada: bitta yozuv, IP xodimning o'zi kiritgani,
    telefon fayldan."""
    uc = _use_case(monkeypatch, [USER_EMP])
    kind, emps = await uc._employee_route("abrorov ip raqami")
    assert kind == "answer" and len(emps) == 1
    assert emps[0]["ip"] == "2410"
    assert emps[0]["phone"] == VEC_EMP["phone"]


@pytest.mark.asyncio
async def test_old_file_ip_not_found_when_user_entered_new(monkeypatch: pytest.MonkeyPatch) -> None:
    """Faylda 2402, o'zi 2410 kiritgan — eski 2402 bo'yicha u chiqmaydi."""
    uc = _use_case(monkeypatch, [USER_EMP])
    assert await uc._employee_route("2402") == ("no_ip", [])


@pytest.mark.asyncio
async def test_users_number_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    uc = _use_case(monkeypatch, [USER_EMP])
    assert await uc._employee_route("2410") == ("answer", [USER_EMP])


@pytest.mark.asyncio
async def test_falls_back_to_vector(monkeypatch: pytest.MonkeyPatch) -> None:
    uc = _use_case(monkeypatch, [])
    assert await uc._employee_route("abrorov ip raqami") == ("answer", [VEC_EMP])


# --- Ism ham, familiya ham mos kelgani faqat familiyasi mos kelganidan ustun ---

UMIDA = {
    "fish": "UBAYDULLOYEVA UMIDA ILXOMOVNA",
    "department": "SHAHRISABZ BXM",
    "division": "Operatsion blok",
    "position": "Kassir",
    "ip": "",
    "phone": "99 672 11 57",
}
MAFTUNA_FILE = {
    "fish": "UBAYDULLAYEVA MAFTUNA",  # imlo boshqacha: -lla- / -llo-
    "department": "BUXORO BXM",
    "division": "",
    "position": "Universal menedjer",
    "ip": "",
    "phone": "90 111 22 33",
}
MAFTUNA_USER = {
    "fish": "Ubaydulloyeva Maftuna",
    "department": "Buxoro BXM",
    "division": "",
    "position": "Universal menedjer (mutaxassis)",
    "ip": "4120",
    "phone": "",
}
UMIDA_USER = {**MAFTUNA_USER, "fish": "Ubaydulloyeva Umida", "ip": "4121"}


def test_full_name_beats_surname_only_with_spelling_variant() -> None:
    assert _match_employees([UMIDA, MAFTUNA_FILE], "ubaydulloyeva maftuna") == [MAFTUNA_FILE]


def test_surname_only_lists_everyone_with_it() -> None:
    assert _match_employees([UMIDA, MAFTUNA_USER], "ubaydulloyeva") == [UMIDA, MAFTUNA_USER]


def test_different_surnames_are_not_merged() -> None:
    emp = {**UMIDA, "fish": "XUDOYBERDIYEV ANVAR"}
    assert _match_employees([emp], "xudoyberganov") == []


@pytest.mark.asyncio
async def test_file_wins_when_users_match_is_weaker(monkeypatch: pytest.MonkeyPatch) -> None:
    uc = _use_case(monkeypatch, [UMIDA_USER])

    async def points() -> list[dict[str, Any]]:
        return [{**MAFTUNA_FILE, "doc_type": "employee"}]

    monkeypatch.setattr(uc, "_scroll_points", points)
    kind, emps = await uc._employee_route("ubaydulloyeva maftuna")
    assert kind == "answer"
    assert [e["fish"] for e in emps] == ["UBAYDULLAYEVA MAFTUNA"]


@pytest.mark.asyncio
async def test_same_person_merged_user_fields_win(monkeypatch: pytest.MonkeyPatch) -> None:
    uc = _use_case(monkeypatch, [MAFTUNA_USER])

    async def points() -> list[dict[str, Any]]:
        return [{**MAFTUNA_FILE, "doc_type": "employee"}]

    monkeypatch.setattr(uc, "_scroll_points", points)
    kind, emps = await uc._employee_route("ubaydulloyeva maftuna ip raqami")
    assert kind == "answer" and len(emps) == 1
    assert emps[0]["ip"] == "4120"  # o'zi kiritgan
    assert emps[0]["phone"] == MAFTUNA_FILE["phone"]


# --- IP egasi topilmasa: aniq "bu raqamli xodim yo'q" ---


@pytest.mark.parametrize("q", ["4031", "4031?", "4031 kimniki", "ip 4031"])
@pytest.mark.asyncio
async def test_unknown_ip_number(monkeypatch: pytest.MonkeyPatch, q: str) -> None:
    uc = _use_case(monkeypatch, [USER_EMP])
    assert await uc._employee_route(q) == ("no_ip", [])


@pytest.mark.asyncio
async def test_name_with_number_is_not_ip_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    uc = _use_case(monkeypatch, [USER_EMP])
    route = await uc._employee_route("abrorov 4031")
    assert route is not None and route[0] != "no_ip"


@pytest.mark.asyncio
async def test_number_in_product_question_is_not_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    uc = _use_case(monkeypatch, [USER_EMP])
    route = await uc._employee_route("1000 dollar kursi")
    assert route is None or route[0] != "no_ip"


def test_ip_not_found_text_in_all_languages() -> None:
    uz = AnswerQuestionUseCase._employee_canned("no_ip", "4031", "uz")
    cyr = AnswerQuestionUseCase._employee_canned("no_ip", "4031", "uz_cyrl")
    ru = AnswerQuestionUseCase._employee_canned("no_ip", "4031", "ru")
    assert "4031" in uz and "topilmadi" in uz
    assert "4031" in cyr and "топилмади" in cyr
    assert "4031" in ru and "не найден" in ru


# --- IP 2-3 xonali ham bo'ladi ---


@pytest.mark.parametrize(
    ("q", "ip"), [("45", "45"), ("ip 45", "45"), ("512", "512"), ("512 kimniki", "512")]
)
@pytest.mark.asyncio
async def test_short_ip_numbers(monkeypatch: pytest.MonkeyPatch, q: str, ip: str) -> None:
    emp = {**USER_EMP, "ip": ip}
    uc = _use_case(monkeypatch, [emp])
    assert await uc._employee_route(q) == ("answer", [emp])


def test_number_in_sentence_is_not_two_digit_ip() -> None:
    """Gapdagi 2 xonali son ("10 yil") IP deb olinmaydi."""
    from src.knowledge.answer_helpers import _match_by_number

    emp = {**USER_EMP, "ip": "10"}
    assert _match_by_number([emp], "abrorov 10 yil ishlagan") == []
    assert _match_by_number([emp], "it departament 10 ta xodim") == []


# --- Filial bo'yicha: ikkala manbadan, bo'lim yoki lavozimdan ---

SHAHRISABZ_USER = {
    "fish": "Karimov Anvar", "department": "Shahrisabz BXM", "division": "",
    "position": "Kassir", "ip": "301", "phone": "",
}
SHAHRISABZ_FILE = {
    "doc_type": "employee", "fish": "TOSHEVA NODIRA", "department": "SHAHRISABZ BXM",
    "division": "", "position": "Bosh buxgalter", "ip": "302", "phone": "91 000 00 00",
}
BY_POSITION = {
    "doc_type": "employee", "fish": "QODIROV SARDOR", "department": "Chakana biznes departamenti",
    "division": "", "position": "Shahrisabz BXM boshqaruvchisi", "ip": "303", "phone": "",
}
BUXORO_FILE = {
    "doc_type": "employee", "fish": "ALIYEV BOBUR", "department": "BUXORO BXM",
    "division": "", "position": "Kassir", "ip": "401", "phone": "",
}


@pytest.mark.parametrize(
    "q", ["shahrisabz bxm xodimlari", "shahrisabz filiali xodimlari ip raqamlari"]
)
@pytest.mark.asyncio
async def test_branch_employees_from_both_sources(monkeypatch: pytest.MonkeyPatch, q: str) -> None:
    uc = _use_case(monkeypatch, [SHAHRISABZ_USER])

    async def points() -> list[dict[str, Any]]:
        return [SHAHRISABZ_FILE, BY_POSITION, BUXORO_FILE]

    monkeypatch.setattr(uc, "_scroll_points", points)
    kind, emps = await uc._employee_route(q)
    assert kind == "answer"
    assert sorted(e["fish"] for e in emps) == ["Karimov Anvar", "QODIROV SARDOR", "TOSHEVA NODIRA"]


@pytest.mark.asyncio
async def test_branch_info_question_is_not_employee_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """Xodim so'ralmagan filial savoli (manzil, ish vaqti) — xodimlar ro'yxati emas."""
    uc = _use_case(monkeypatch, [SHAHRISABZ_USER])

    async def points() -> list[dict[str, Any]]:
        return [SHAHRISABZ_FILE, {"title": "Shahrisabz BXM", "chunk_text": "Manzil: ..."}]

    monkeypatch.setattr(uc, "_scroll_points", points)
    route = await uc._employee_route("shahrisabz bxm manzili")
    assert route is None or route[0] != "answer"

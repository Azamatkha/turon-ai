"""Bo'lim ro'yxati: users jadvali + vektor baza ARALASH, dublikatsiz,
raqamsiz xodimlarsiz (2026-11-24 IT departamenti holati)."""

from typing import Any

import pytest

from src.knowledge import usecases as uc_mod
from src.knowledge.answer_helpers import (
    _display_name,
    _kb_employees,
    _match_by_number,
    _merge_employee_sources,
    _sort_by_ip,
)
from src.knowledge.usecases import AnswerQuestionUseCase

IT_USERS = "Axborot texnologiyalari departamenti (IT departamenti)"


def _user(fish: str, ip: str = "", phone: str = "", position: str = "Mutaxassis") -> dict[str, Any]:
    return {"fish": fish, "department": IT_USERS, "division": "", "position": position, "ip": ip, "phone": phone}


USERS = [
    _user("Ibragimov Zakir Yakubovich", position="Departament direktori"),  # raqami faqat faylda
    _user("Xamdamov Azamat Shuxrat O‘g‘li"),  # raqami faqat faylda
    _user("Mansurov Akbar Zayniddin O‘g‘li"),  # hech qayerda raqami yo'q
    _user("Turdiboyev Ixtiyor Shakir O‘g‘li", ip="2213"),
]

# Excel'dan yuklangan, keyin admin TAHRIRLAGAN yozuv: doc_type yo'q, sarlavha o'zgargan
EDITED_TEXT = {
    "title": IT_USERS,
    "chunk_text": (
        "Bo'lim: IT DEPARTAMENT. Lavozim: Chief Data Officer. F.I.SH: KULMATOV XAYRULLO "
        "XABIBULLOYEVICH. Ichki raqam (IP): 2201.\n\n"
        "Bo'lim: IT DEPARTAMENT. Lavozim: Departament direktori. F.I.SH: IBRAGIMOV ZAKIR "
        "YAKUBOVICH. Ichki raqam (IP): 2200.\n\n"
        "Bo'lim: IT DEPARTAMENT. Lavozim: Junior backend dasturchi. F.I.SH: XAMDAMOV AZAMAT "
        "SHUXRAT O‘G‘LI. Ichki raqam (IP): 2207."
    ),
}
# Boshqa bo'limning odatiy (strukturaviy) xodim yozuvi
OTHER_DEPT = {
    "doc_type": "employee", "title": "AUDIT", "fish": "Aliyev Vali", "department": "AUDIT",
    "division": "", "position": "Auditor", "ip": "3100", "phone": "",
}


def test_edited_employee_text_is_still_read() -> None:
    emps, titles = _kb_employees([OTHER_DEPT, EDITED_TEXT, {"title": "Kredit", "chunk_text": "foiz 20%"}])
    assert {e["ip"] for e in emps} == {"3100", "2201", "2200", "2207"}
    assert titles == {"AUDIT", IT_USERS}


def test_file_only_people_get_users_department_name() -> None:
    emps, _ = _kb_employees([EDITED_TEXT])
    merged = _merge_employee_sources(USERS, emps)
    kulmatov = next(e for e in merged if "KULMATOV" in e["fish"])
    assert kulmatov["department"] == IT_USERS
    # Bir odam ikkala manbada — bitta yozuv, raqami fayldan to'ldirilgan
    ibragimov = [e for e in merged if "Ibragimov" in e["fish"] or "IBRAGIMOV" in e["fish"]]
    assert len(ibragimov) == 1 and ibragimov[0]["ip"] == "2200"


def _use_case(monkeypatch: pytest.MonkeyPatch) -> AnswerQuestionUseCase:
    uc = AnswerQuestionUseCase(embedder=None, store=None, ai_client=None)  # type: ignore[arg-type]

    async def fake_users() -> list[dict[str, Any]]:
        return USERS

    async def fake_points() -> list[dict[str, Any]]:
        return [OTHER_DEPT, EDITED_TEXT]

    async def no_ip(q: str) -> list[dict[str, Any]]:
        return []

    monkeypatch.setattr(uc_mod, "directory_users", fake_users)
    monkeypatch.setattr(uc, "_scroll_points", fake_points)
    monkeypatch.setattr(uc, "_lookup_by_ip_field", no_ip)
    return uc


@pytest.mark.asyncio
async def test_department_list_is_mixed_deduped_and_reachable(monkeypatch: pytest.MonkeyPatch) -> None:
    uc = _use_case(monkeypatch)
    route = await uc._employee_route("IT departamenti ichki raqami")
    assert route is not None and route[0] == "answer"
    ips = sorted(e["ip"] for e in route[1])
    # Kulmatov (faqat faylda), Ibragimov va Xamdamov (raqami fayldan), Turdiboyev (users)
    assert ips == ["2200", "2201", "2207", "2213"]
    # Raqamsiz Mansurov ro'yxatda yo'q
    assert not any("Mansurov" in e["fish"] for e in route[1])
    # Bir xil savol — bir xil ro'yxat
    again = await uc._employee_route("IT departamenti ichki raqami")
    assert again is not None and [e["fish"] for e in again[1]] == [e["fish"] for e in route[1]]


@pytest.mark.asyncio
async def test_person_without_contact_still_found_by_name(monkeypatch: pytest.MonkeyPatch) -> None:
    uc = _use_case(monkeypatch)
    route = await uc._employee_route("Akbar Mansurov ichki raqami")
    assert route is not None and route[0] == "answer"
    assert "Mansurov" in route[1][0]["fish"]


def test_same_person_twice_in_file_becomes_one_line() -> None:
    text = {
        "title": "IT",
        "chunk_text": (
            "Bo'lim: IT DEPARTAMENT. Lavozim: CDO. F.I.SH: KULMATOV XAYRULLO "
            "XABIBULLOYEVICH. Ichki raqam (IP): 2201.\n\n"
            "Bo'lim: IT DEPARTAMENT. Lavozim: CDO. F.I.SH: KULMATOV XAYRULLO "
            "XABIBULLOYEVICH. Ichki raqam (IP): 2199."
        ),
    }
    emps, _ = _kb_employees([text])
    assert len(emps) == 1 and emps[0]["ip"] == "2199, 2201"
    # Ikkala raqam bo'yicha ham topiladi
    assert _match_by_number(emps, "2199 kimniki") == emps
    assert _match_by_number(emps, "2201") == emps


def test_display_name_and_ip_order() -> None:
    assert _display_name("G‘ANIYEV ABDUMUTAL SUVANOVICH") == "G‘aniyev Abdumutal Suvanovich"
    assert _display_name("SADULLAYEV ABDULLA UBAYDULLA O‘G‘LI") == "Sadullayev Abdulla Ubaydulla O‘g‘li"
    assert _display_name("Xamdamov Azamat") == "Xamdamov Azamat"
    emps = [
        {"fish": "B", "ip": "", "phone": "+998 90"},
        {"fish": "C", "ip": "2201"},
        {"fish": "A", "ip": "", "phone": "+998 91"},
        {"fish": "D", "ip": "272"},
        {"fish": "E", "ip": "2199, 2205"},
    ]
    assert [e["fish"] for e in _sort_by_ip(emps)] == ["D", "E", "C", "A", "B"]


@pytest.mark.asyncio
async def test_department_list_sorted_by_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    route = await _use_case(monkeypatch)._employee_route("IT departamenti ichki raqami")
    assert route is not None
    assert [e["ip"] for e in route[1]] == ["2200", "2201", "2207", "2213"]

"""2026-11-19 server logidagi holatlar:

* "IP ni qanday qoshsam boladi" — ilovadan foydalanish savoli, xodim qidiruvi
  emas (ilgari "xodim topilmadi" qaytardi);
* "Inoyatov suxrob" — familiya bazada yo'q, ism bor: ro'yxat JIM berilmaydi;
* kod tuzgan javoblar (xodim, "topilmadi") fonda AI tahlilidan o'tadi.
"""

from typing import Any

import pytest

from src.chat.answer_review import needs_review
from src.knowledge.answer_helpers import (
    _asks_contacts_howto,
    _format_employee_answer,
    _match_employees_ex,
)


@pytest.mark.parametrize(
    "q",
    [
        "IP ni qanday qoshsam boladi",
        "ip raqamimni qayerga kiritaman",
        "ichki raqamimni qanday o'zgartiraman",
        "telefon raqamimni yangilamoqchiman",
        "Как добавить свой внутренний номер",
        "ИП ни қандай қўшсам бўлади",
    ],
)
def test_contacts_howto_detected(q: str) -> None:
    assert _asks_contacts_howto(q)


@pytest.mark.parametrize(
    "q",
    [
        "2206 kimniki",
        "Xamdamov ip raqami",
        "IT departament ichki raqamlari",
        "kredit qanday olinadi",
    ],
)
def test_contacts_howto_not_lookup(q: str) -> None:
    assert not _asks_contacts_howto(q)


def _emp(fish: str, dept: str = "Buxoro BXM") -> dict[str, Any]:
    return {"fish": fish, "department": dept, "division": "", "position": "Mutaxassis", "ip": "4010", "phone": ""}


SUXROBS = [_emp("Odilov Suxrob Sodikovich"), _emp("Xamroyev Suxrob Abduxalimovich", "Operatsion")]


def test_unknown_surname_is_said_out_loud() -> None:
    emps, note = _match_employees_ex(SUXROBS, "inoyatov suxrob")
    assert emps == SUXROBS
    assert note == "«Inoyatov» familiyali xodim bazada topilmadi. «Suxrob» ismli 2 ta xodim bor:"
    text = _format_employee_answer(emps, "", note)
    assert text.startswith("«Inoyatov» familiyali xodim bazada topilmadi.")


def test_known_surname_has_no_note() -> None:
    emps, note = _match_employees_ex(SUXROBS, "odilov suxrob")
    assert emps == [SUXROBS[0]]
    assert note is None


def test_review_only_unchecked_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.main.config import config

    monkeypatch.setattr(config.ai, "ANSWER_VERIFY", True)
    assert needs_review("answered", None, "1. Odilov Suxrob ...")
    assert needs_review("no_info", None, "Bu so'rov bo'yicha xodim topilmadi.")
    # Asosiy oqimda allaqachon tekshirilgan yoki keshdan
    assert not needs_review("answered", "ok", "javob")
    assert not needs_review("answered", "cached", "javob")
    # Xavfsizlik bloklari va bo'sh javob
    assert not needs_review("blocked", None, "javob")
    assert not needs_review("answered", None, "  ")


@pytest.mark.asyncio
async def test_admin_message_needs_text_or_image() -> None:
    from uuid import uuid4

    from src.admin.usecases import SendUserMessageUseCase
    from src.core.errors.exceptions import NotAcceptableException

    with pytest.raises(NotAcceptableException):
        await SendUserMessageUseCase(uow=None).execute(uuid4(), "   ", None)  # type: ignore[arg-type]

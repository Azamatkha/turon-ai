"""Bir martalik tarjima: "ruschaga tarjima qilib ber: <matn>" tarjimonga ketadi.

Ilgari bunday so'rov umumiy chat (til savoli) yo'liga tushib, u yerdagi
"javob o'zbekcha" qoidasi tufayli matn ruschaga emas, o'zbekchada qaytardi.
"""

import pytest

from src.translator.usecases import TranslatorUseCase, parse_one_shot

TEXT = (
    "MS Store’dagi aniq manzillarni topa olmadim.\n\n"
    "D-Island: Windows 10 va 11 uchun. Manzil: github.com/H7gamer/d-island/releases"
)


@pytest.mark.parametrize(
    "question,expected",
    [
        (f'ruschaga tarjimaga qilib ber\n"{TEXT}"', ("ru", TEXT)),
        (f"inglizchaga tarjima qilib ber: {TEXT}", ("en", TEXT)),
        (f"{TEXT}\nshuni rus tiliga o'girib ber", ("ru", TEXT)),
        ("Переведи на английский: срок кредита", ("en", "срок кредита")),
        ("русчага таржима қил: kredit muddati", ("ru", "kredit muddati")),
        ("o‘zbekchaga tarjima qil: срок кредита", ("uz", "срок кредита")),
        ("kirillga o'gir: kredit muddati", ("uz_cyrl", "kredit muddati")),
    ],
)
def test_parse_one_shot(question: str, expected: tuple[str, str]) -> None:
    assert parse_one_shot(question) == expected


@pytest.mark.parametrize(
    "question",
    [
        "ruschaga tarjima qilib ber",  # matn yo'q
        "mutolaa so'zining ma'nosi nima",
        "rus tilida gapiradigan mijoz keldi, unga kredit haqida nima deyman",
        # Ko'rsatma emas, uzun gap: til nomi matn o'rtasida
        "Kecha mijoz keldi va u menga ruschaga tarjima qilingan shartnoma olib "
        "keldi, lekin unda xatolar ko'p edi\nnima qilsam bo'ladi",
    ],
)
def test_not_one_shot(question: str) -> None:
    assert parse_one_shot(question) is None


@pytest.mark.asyncio
async def test_prepare_routes_one_shot_without_session() -> None:
    uc = TranslatorUseCase(uow=None, ai_client=None)  # type: ignore[arg-type]
    step = await uc.prepare(user_id=None, session_id=None, question=f"ruschaga tarjima qil: {TEXT}")  # type: ignore[arg-type]
    assert step is not None
    assert step.target == "ru"
    assert step.text == TEXT


@pytest.mark.asyncio
async def test_prepare_ignores_normal_question_without_session() -> None:
    uc = TranslatorUseCase(uow=None, ai_client=None)  # type: ignore[arg-type]
    assert await uc.prepare(user_id=None, session_id=None, question="kredit foizi qancha") is None  # type: ignore[arg-type]

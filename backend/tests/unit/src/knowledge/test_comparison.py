"""Turkum ichida solishtirish ("eng foizi past 3 ta kredit"): kontekstga
turkumdagi HAR mahsulotning shartlari beriladi; javob tekshiruvi qayta
yozilganda ikkala tahlil saqlanadi."""

from typing import Any

import pytest

from src.knowledge.answer_helpers import asks_comparison, terms_digest
from src.knowledge.verifier import join_review_notes, split_review_notes


def _doc(title: str, text: str, **extra: Any) -> dict[str, Any]:
    return {"title": title, "chunk_index": 0, "chunk_text": text, "source_url": "", **extra}


@pytest.mark.parametrize(
    ("q", "want"),
    [
        ("eng foizi past 3ta kredit ni ko'rsata", True),
        ("qaysi omonat daromadliroq", True),
        ("Самый низкий процент по кредиту", True),
        ("Kreditlar ro'yxati", False),
        ("Avtokredit hujjatlari", False),
    ],
)
def test_asks_comparison(q: str, want: bool) -> None:
    assert asks_comparison(q, q.lower()) is want


def test_terms_digest_keeps_rates_first() -> None:
    text = (
        "Mahsulot haqida umumiy ma'lumot. Kredit miqdori: 100 mln so'mgacha. "
        "Foiz stavkasi: 12 oygacha — 26,9%. Bank juda qadimiy tarixga ega."
    )
    out = terms_digest(text, 60)
    assert "26,9%" in out
    assert "tarix" not in out
    # Byudjet yetsa raqamli shart ham qo'shiladi, asl tartibda
    full = terms_digest(text, 500)
    assert full.index("100 mln") < full.index("26,9%")
    assert "umumiy" not in full


def test_terms_digest_without_terms_falls_back_to_start() -> None:
    assert terms_digest("Oddiy matn raqamsiz", 10) == "Oddiy matn"


@pytest.mark.asyncio
async def test_comparison_gives_every_product_of_category() -> None:
    """Vektor qidiruv emas — Kreditlar turkumidagi HAMMA mahsulot foizi
    kontekstga tushadi, omonat esa tushmaydi."""
    from src.knowledge.usecases import AnswerQuestionUseCase

    uc = AnswerQuestionUseCase(embedder=None, store=None, ai_client=None)  # type: ignore[arg-type]
    points = [
        _doc("Avtokredit", "Avtomobil uchun. Stavka: 22%.", category="credit"),
        _doc("Ipoteka", "Uy uchun kredit. Stavka: 18%.", category="credit"),
        _doc("Mikroqarz", "Stavka: 28,9%. Tarix.", category="credit"),
        _doc("Meros omonati", "Daromad: 20%.", category="deposit"),
    ]

    async def _scroll() -> list[dict[str, Any]]:
        return points

    uc._scroll_points = _scroll  # type: ignore[method-assign]
    results = await uc._comparison_results("eng foizi past 3 ta kredit")
    titles = [p["title"] for p, _ in results]
    assert sorted(titles) == ["Avtokredit", "Ipoteka", "Mikroqarz"]
    texts = " ".join(p["chunk_text"] for p, _ in results)
    assert "22%" in texts and "18%" in texts and "28,9%" in texts

    prompt, _ = await uc._assemble("eng foizi past 3 ta kredit", None, results, include_catalog=False, compare=True)
    assert "EVERY product" in prompt

    # Solishtirish bo'lmagan savol — odatdagi qidiruv
    assert await uc._comparison_results("Avtokredit hujjatlari") == []


def test_review_notes_roundtrip() -> None:
    note = join_review_notes("1-variant: foizlar to'qilgan", "Qayta yozilgan javob to'g'ri")
    assert split_review_notes(note) == ("1-variant: foizlar to'qilgan", "Qayta yozilgan javob to'g'ri")
    # Eski (bitta) tahlil — o'zgarishsiz
    assert split_review_notes("oddiy tahlil") == (None, "oddiy tahlil")
    assert split_review_notes(None) == (None, None)

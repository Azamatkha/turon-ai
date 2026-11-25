"""Turkum ro'yxati mijoz turi (jismoniy/yuridik) bo'yicha: guruhlash,
"yuridik" deb davom ettirish, aytilmasa — jismoniy shaxs."""

from typing import Any

import pytest

from src.knowledge.categories import (
    AUDIENCE_HEADINGS,
    audience_followup,
    audience_groups,
)
from src.knowledge.schemas import ChatTurn


def _doc(title: str, text: str, audience: str = "", category: str = "credit") -> dict[str, Any]:
    return {
        "title": title,
        "chunk_index": 0,
        "chunk_text": text,
        "source_url": "",
        "category": category,
        "audience": audience,
    }


POINTS = [
    _doc("Avtokredit", "Stavka: 22%.", "individual"),
    _doc("Biznes kredit", "Stavka: 19%.", "legal"),
    _doc("Mikroqarz", "Stavka: 28,9%.", "individual"),
    _doc("Universal kredit", "Stavka: 25%.", "both"),
    _doc("Eski kredit", "Stavka: 30%."),
]


def _use_case() -> Any:
    from src.knowledge.usecases import AnswerQuestionUseCase

    uc = AnswerQuestionUseCase(embedder=None, store=None, ai_client=None)  # type: ignore[arg-type]

    async def _scroll() -> list[dict[str, Any]]:
        return POINTS

    uc._scroll_points = _scroll  # type: ignore[method-assign]
    return uc


def test_audience_groups_numbering_is_continuous() -> None:
    out = audience_groups(
        [("A", "individual"), ("B", "legal"), ("C", "individual"), ("D", "both"), ("E", "")]
    )
    assert out is not None
    lines = out.splitlines()
    assert lines[0] == AUDIENCE_HEADINGS["individual"]
    assert lines[1:3] == ["1. A", "2. C"]
    assert AUDIENCE_HEADINGS["legal"] in lines and "3. B" in lines
    assert "4. D" in lines and "5. E" in lines
    # Faqat bitta mijoz turi — guruhlash shart emas
    assert audience_groups([("A", "individual"), ("B", "")]) is None
    assert audience_groups([("A", "legal"), ("B", "both")]) is None


def test_audience_groups_cyrillic_headings() -> None:
    out = audience_groups([("Avto", "individual"), ("Biznes", "legal")], cyrillic=True)
    assert out is not None
    assert "Жисмоний" in out and "1. Avto" in out


@pytest.mark.asyncio
async def test_broad_list_grouped_by_audience() -> None:
    reply, title = await _use_case()._broad_category_reply("kredit turlari", False)
    assert title is None and reply is not None
    ind = reply.index(AUDIENCE_HEADINGS["individual"])
    leg = reply.index(AUDIENCE_HEADINGS["legal"])
    assert ind < reply.index("Avtokredit") < leg < reply.index("Biznes kredit")
    assert "jismoniy" in reply.split("\n\n")[-1].lower()


@pytest.mark.asyncio
async def test_broad_list_with_audience_is_filtered_not_grouped() -> None:
    reply, _ = await _use_case()._broad_category_reply("yuridik shaxslar uchun kredit turlari", False)
    assert reply is not None
    assert "Biznes kredit" in reply and "Avtokredit" not in reply
    assert AUDIENCE_HEADINGS["legal"] not in reply


def test_audience_followup() -> None:
    listed = f"{AUDIENCE_HEADINGS['individual']}\n1. A\n\n{AUDIENCE_HEADINGS['legal']}\n2. B"
    assert audience_followup("yuridik", listed, "kredit turlari") == "kredit turlari yuridik"
    assert audience_followup("jismoniy shaxslar uchun", listed, "kredit turlari") == (
        "kredit turlari jismoniy shaxslar uchun"
    )
    # Boshqa savol, oddiy ro'yxat yoki tarix yo'q — o'zgarmaydi
    assert audience_followup("yuridik shaxslar uchun omonat foizi qancha", listed, "x") is None
    assert audience_followup("yuridik", "1. A\n2. B", "kredit turlari") is None
    assert audience_followup("2", listed, "kredit turlari") is None
    assert audience_followup("yuridik", None, None) is None


def test_followup_from_history() -> None:
    from src.knowledge.usecases import _audience_followup_question

    listed = f"{AUDIENCE_HEADINGS['individual']}\n1. A\n\n{AUDIENCE_HEADINGS['legal']}\n2. B"
    history = [
        ChatTurn(role="user", content="kredit turlari"),
        ChatTurn(role="assistant", content=listed),
    ]
    assert _audience_followup_question("yuridik", history) == "kredit turlari yuridik"
    assert _audience_followup_question("yuridik", None) is None


@pytest.mark.asyncio
async def test_comparison_defaults_to_individual() -> None:
    uc = _use_case()
    titles = sorted(p["title"] for p, _ in await uc._comparison_results("eng foizi past kredit"))
    # Yuridik "Biznes kredit" yo'q; "ikkalasi" va belgilanmagan qoladi
    assert titles == ["Avtokredit", "Eski kredit", "Mikroqarz", "Universal kredit"]
    legal = sorted(
        p["title"] for p, _ in await uc._comparison_results("yuridik shaxslar uchun eng past foizli kredit")
    )
    assert legal == ["Biznes kredit", "Eski kredit", "Universal kredit"]


@pytest.mark.asyncio
async def test_word_from_category_name_is_not_a_condition(monkeypatch: pytest.MonkeyPatch) -> None:
    """"Xalqaro pul o'tkazmalari" turkumi: savoldagi "xalqaro" — turkum NOMI,
    qo'shimcha shart emas. Ilgari ro'yxat o'rniga model 3 tasini aytardi."""
    from src.knowledge import usecases
    from src.knowledge.categories import make_def

    async def _cats() -> list[Any]:
        return [make_def("transfer", "Xalqaro pul o'tkazmalari", "o'tkazma, otkazma")]

    monkeypatch.setattr(usecases, "kb_categories", _cats)
    names = ["Astrasend", "Western Union", "Zolotaya Korona", "UPT", "Money Gram"]
    uc = _use_case()
    points = [_doc(n, "pul o'tkazmasi", "individual", "transfer") for n in names]

    async def _scroll() -> list[dict[str, Any]]:
        return points

    uc._scroll_points = _scroll
    reply, title = await uc._broad_category_reply("xalqaro pul o'tkazmalari", False)
    assert title is None and reply is not None
    assert all(n in reply for n in names)

"""Savoldagi bitta tasodifiy so'z mahsulot/sahifa nomiga yopishib qolmasin."""

from typing import Any

import pytest

from src.knowledge.usecases import AnswerQuestionUseCase

TITLES = ["Meros omonati", "Biz bilan bog'lanish", "Tez pul mikroqarz", "Green Avto krediti"]


def _uc(monkeypatch: pytest.MonkeyPatch) -> AnswerQuestionUseCase:
    uc = AnswerQuestionUseCase(embedder=None, store=None, ai_client=None)  # type: ignore[arg-type]

    async def groups(*a: Any, **kw: Any) -> dict:
        return {"x": [(t, None) for t in TITLES]}

    monkeypatch.setattr(uc, "_catalog_groups_detailed", groups)
    return uc


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "question,exact,partial",
    [
        # Rasmdagi holat: "bilan" so'zi «Biz bilan bog'lanish» ga yopishmasin
        ("markaziy bank qaysi banklar bilan hamkorlikda ishlaydi", None, []),
        ("tez javob bering", None, []),
        ("meros omonati shartlari", "Meros omonati", []),
        ("meros haqida ma'lumot", None, ["Meros omonati"]),
        ("green avto", None, ["Green Avto krediti"]),
        ("avto", None, []),
    ],
)
async def test_title_match(
    monkeypatch: pytest.MonkeyPatch, question: str, exact: str | None, partial: list[str]
) -> None:
    got_exact, got_partial = await _uc(monkeypatch)._catalog_title_match(question)
    assert got_exact == exact
    assert got_partial == partial

"""Umumiy "valyuta kursi" savoli: model chaqirilmaydi, asosiy kanal bo'yicha
barcha valyutalar va kurs oynasi haqida maslahat chiqadi."""

import json
from typing import Any

import pytest

from src.knowledge.prompts import RATES_PANEL_HINT, RU_CANNED_REPLIES
from src.knowledge.usecases import AnswerQuestionUseCase

RATES = {
    "stamp": "11.11.2026 09:00:00",
    "channels": [
        {
            "key": "tab1",
            "label": "Ayirboshlash shoxobchasida",
            "rows": [
                {"code": "USD", "name": "AQSh dollari", "buy": 11920, "sell": 12000, "cb": 11974.02},
                {"code": "EUR", "name": "Evro", "buy": 12500, "sell": 14500, "cb": 13432.46},
                {"code": "KZT", "name": "Qozog'iston tengesi", "buy": 15, "sell": 30, "cb": 26.8},
            ],
        },
        {
            "key": "tab2",
            "label": "Ilovada (MyTuron mobil ilovasida)",
            "rows": [{"code": "USD", "name": "AQSh dollari", "buy": 11930, "sell": 11990, "cb": 11974.02}],
        },
    ],
}


class _Store:
    async def search_by_field(self, field: str, value: str, limit: int = 40) -> list[dict[str, Any]]:
        return [{"rates_json": json.dumps(RATES)}]


class _NoModel:
    async def generate_text_with_usage(self, *a: Any, **kw: Any) -> Any:
        raise AssertionError("umumiy savolda model chaqirilmasligi kerak")


def _uc() -> AnswerQuestionUseCase:
    return AnswerQuestionUseCase(embedder=None, store=_Store(), ai_client=_NoModel())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_general_question_lists_all_currencies() -> None:
    res = await _uc()._rates_reply("valyuta kursi", "valyuta kursi", None, "uz")
    assert res is not None
    text, tokens = res
    assert tokens == 0
    for code in ("USD", "EUR", "KZT"):
        assert code in text
    assert "Ilovada" not in text  # faqat asosiy kanal
    assert text.endswith(RATES_PANEL_HINT)


@pytest.mark.asyncio
async def test_general_question_hint_in_russian() -> None:
    res = await _uc()._rates_reply("курс валют", "valyuta kursi", None, "ru")
    assert res is not None
    assert res[0].endswith(RU_CANNED_REPLIES[RATES_PANEL_HINT])

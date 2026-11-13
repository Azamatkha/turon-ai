from typing import Any

import pytest

from src.chat import answer_cache as ac
from src.core.vectorstore.version import KB_VERSION_KEY
from src.knowledge.schemas import ChatTurn
from tests.fakes.redis import InMemoryRedis


class _FakeUseCase:
    """execute_stream'ni taqlid qiladi: necha marta chaqirilganini sanaydi."""

    def __init__(self, intent: str = "product", outcome: str = "answered", finish: str = "stop") -> None:
        self.intent, self.outcome, self.finish = intent, outcome, finish
        self.calls = 0
        self.last_intent: str | None = None
        self.last_outcome = "answered"
        self.last_top_score: float | None = None
        self.last_verdict: str | None = None

    async def execute_stream(self, question: str, history: Any) -> Any:
        self.calls += 1
        self.last_intent, self.last_outcome, self.last_top_score = self.intent, self.outcome, 0.81
        yield {"type": "status", "step": "analyze"}
        yield {"type": "delta", "text": "Kredit foizi "}
        yield {"type": "delta", "text": "22%."}
        yield {"type": "done", "finish_reason": self.finish, "sources": [{"title": "Kredit", "score": 0.81}]}


async def _run(uc: _FakeUseCase, redis: InMemoryRedis, q: str, history: Any = None) -> list[dict]:
    return [ev async for ev in ac.cached_answer_stream(uc, q, history, redis)]  # type: ignore[arg-type]


def _text(events: list[dict]) -> str:
    return "".join(e.get("text", "") for e in events if e["type"] == "delta")


@pytest.mark.asyncio
async def test_second_identical_question_served_from_cache() -> None:
    redis, uc = InMemoryRedis(), _FakeUseCase()
    first = await _run(uc, redis, "Kredit foizi qancha?")
    # Boshqa yozilishi (katta harf, tinish) — baribir bitta kalit
    second = await _run(uc, redis, "kredit foizi qancha")
    assert uc.calls == 1
    assert _text(second) == _text(first) == "Kredit foizi 22%."
    done = second[-1]
    assert done["finish_reason"] == ac.CACHED_FINISH_REASON
    assert done["sources"] == [{"title": "Kredit", "score": 0.81}]
    assert uc.last_intent == "product" and uc.last_outcome == "answered"
    assert await ac.cache_stats_today(redis) == (1, 1)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_kb_change_invalidates() -> None:
    redis, uc = InMemoryRedis(), _FakeUseCase()
    await _run(uc, redis, "Kredit foizi qancha?")
    await redis.incr(KB_VERSION_KEY)  # hujjat qo'shildi/o'zgardi
    await _run(uc, redis, "Kredit foizi qancha?")
    assert uc.calls == 2


@pytest.mark.parametrize(
    ("kwargs", "question", "history"),
    [
        ({"intent": "employee"}, "Aliyev ichki raqami", None),
        ({"intent": "rates"}, "Dollar kursi qancha?", None),
        ({"outcome": "no_info"}, "Noma'lum mahsulot shartlari", None),
        ({"finish": "length"}, "Kredit turlari qanday?", None),
        ({}, "Kartam 4111 1111 1111 1111 bloklandi nima qilay?", None),
        ({}, "Uning foizi qancha?", [ChatTurn(role="user", content="Ta'lim krediti")]),
    ],
)
@pytest.mark.asyncio
async def test_not_cached(kwargs: dict, question: str, history: Any) -> None:
    redis, uc = InMemoryRedis(), _FakeUseCase(**kwargs)
    await _run(uc, redis, question, history)
    await _run(uc, redis, question, history)
    assert uc.calls == 2

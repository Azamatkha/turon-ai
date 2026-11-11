"""Veb-qidiruv zaxirasi: faqat ruxsat etilgan saytlar, maxfiylik, yiqilmaslik."""

from typing import Any

import pytest

from src.knowledge import web_search
from src.knowledge.prompts import NO_INFO_REPLY, WEB_NOTE
from src.knowledge.router import Intent, Route
from src.knowledge.usecases import AnswerQuestionUseCase, _web_eligible
from src.knowledge.web_search import WebHit, build_query, is_allowed_url
from src.main.config import config

DOMAINS = ["cbu.uz", "lex.uz"]


@pytest.fixture
def enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.web_search, "WEB_SEARCH_ENABLED", True)
    monkeypatch.setattr(config.web_search, "WEB_SEARCH_ALLOWED_DOMAINS", ",".join(DOMAINS))
    web_search._cache.clear()


@pytest.mark.parametrize(
    "url,ok",
    [
        ("https://cbu.uz/uz/monetary-policy/", True),
        ("https://www.cbu.uz/x", True),
        ("http://lex.uz/docs/123", True),
        ("https://evilcbu.uz/x", False),
        ("https://cbu.uz.evil.com/x", False),
        ("ftp://cbu.uz/x", False),
        ("https://example.com/?u=cbu.uz", False),
        ("javascript:alert(1)", False),
    ],
)
def test_allowlist(url: str, ok: bool) -> None:
    assert is_allowed_url(url, DOMAINS) is ok


def test_build_query() -> None:
    assert build_query("stavka", DOMAINS) == "stavka (site:cbu.uz OR site:lex.uz)"


@pytest.mark.asyncio
async def test_disabled_does_not_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.web_search, "WEB_SEARCH_ENABLED", False)

    async def boom(q: str) -> Any:
        raise AssertionError("SearXNG chaqirilmasligi kerak edi")

    monkeypatch.setattr(web_search, "_searxng", boom)
    assert await web_search.search("qayta moliyalash stavkasi") == []


@pytest.mark.asyncio
async def test_searxng_failure_returns_empty(enabled: None, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail(q: str) -> Any:
        raise TimeoutError("timeout")

    monkeypatch.setattr(web_search, "_searxng", fail)
    assert await web_search.search("qayta moliyalash stavkasi") == []


@pytest.mark.asyncio
async def test_pii_masked_before_sending(enabled: None, monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[str] = []

    async def capture(q: str) -> list:
        sent.append(q)
        return []

    monkeypatch.setattr(web_search, "_searxng", capture)
    await web_search.search("karta 8600 4904 1234 5678 9 bloklandi 4111111111111111")
    assert sent and "4111111111111111" not in sent[0]


@pytest.mark.parametrize(
    "intent,question,ok",
    [
        (Intent.PRODUCT, "Qayta moliyalash stavkasi qancha", True),
        (Intent.CONCEPT, "Inflyatsiya darajasi qancha", True),
        (Intent.EMPLOYEE, "Karimov telefoni", False),
        (Intent.HISTORY, "oldin nima deding", False),
        (Intent.OTHER, "futbol natijasi", False),
        (Intent.HARMFUL, "oq kukun", False),
    ],
)
def test_eligibility(enabled: None, intent: Intent, question: str, ok: bool) -> None:
    assert _web_eligible(Route(intent=intent, search_query=question), question) is ok


def test_not_eligible_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.web_search, "WEB_SEARCH_ENABLED", False)
    assert not _web_eligible(Route(intent=Intent.PRODUCT, search_query="x"), "Stavka qancha")


class _FakeAI:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompts: list[str] = []

    async def stream_generate(self, prompt: str, **kw: Any) -> Any:
        self.prompts.append(prompt)
        for i in range(0, len(self.reply), 4):
            yield {"type": "delta", "text": self.reply[i : i + 4]}
        yield {"type": "done", "completion_tokens": 7, "finish_reason": "stop"}


def _uc(monkeypatch: pytest.MonkeyPatch, ai: _FakeAI) -> AnswerQuestionUseCase:
    uc = AnswerQuestionUseCase(embedder=None, store=None, ai_client=ai)  # type: ignore[arg-type]

    async def empty(*a: Any, **kw: Any) -> Any:
        return []

    async def no_results(*a: Any, **kw: Any) -> Any:
        return [], []

    async def none_route(*a: Any, **kw: Any) -> Any:
        return None

    async def classify(question: str, history: Any = None) -> Route:
        return Route(intent=Intent.PRODUCT, search_query="qayta moliyalash stavkasi")

    async def broad(*a: Any, **kw: Any) -> Any:
        return None, None

    async def catalog(*a: Any, **kw: Any) -> Any:
        return None, []

    monkeypatch.setattr(uc, "_directory_hits", empty)
    monkeypatch.setattr(uc, "_employee_route", none_route)
    monkeypatch.setattr(uc, "_broad_category_reply", broad)
    monkeypatch.setattr(uc, "_catalog_title_match", catalog, raising=False)
    monkeypatch.setattr(uc, "_search_chunks", no_results)
    monkeypatch.setattr(uc.router, "classify", classify)
    return uc


async def _run(uc: AnswerQuestionUseCase, q: str) -> tuple[str, dict]:
    text, done = "", {}
    async for ev in uc.execute_stream(q):
        if ev["type"] == "delta":
            text += ev["text"]
        elif ev["type"] == "done":
            done = ev
    return text, done


HIT = WebHit(
    url="https://cbu.uz/uz/press/rate",
    title="Asosiy stavka",
    text="Markaziy bank asosiy stavkasini yillik 13.5 foiz darajasida saqlab qoldi. " * 3,
)


@pytest.mark.asyncio
async def test_web_answer_when_kb_empty(enabled: None, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_search(q: str) -> list[WebHit]:
        assert q == "qayta moliyalash stavkasi"  # xom savol emas, router so'rovi
        return [HIT]

    monkeypatch.setattr(web_search, "search", fake_search)
    ai = _FakeAI("Asosiy stavka yillik 13,5 foiz [1].")
    uc = _uc(monkeypatch, ai)
    text, done = await _run(uc, "Markaziy bank stavkasi hozir qancha?")
    assert uc.last_outcome == "web"
    assert text.startswith(WEB_NOTE)
    assert "13,5 foiz [1]" in text
    assert done["sources"][0]["url"] == HIT.url
    assert done["sources"][0]["kind"] == "web"


@pytest.mark.asyncio
async def test_model_not_found_falls_back(enabled: None, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_search(q: str) -> list[WebHit]:
        return [HIT]

    monkeypatch.setattr(web_search, "search", fake_search)
    uc = _uc(monkeypatch, _FakeAI("NOT_FOUND"))
    text, done = await _run(uc, "Markaziy bank stavkasi hozir qancha?")
    assert uc.last_outcome == "no_info"
    assert text == NO_INFO_REPLY
    assert done["sources"] == []


@pytest.mark.asyncio
async def test_no_pages_falls_back(enabled: None, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_search(q: str) -> list[WebHit]:
        return []

    monkeypatch.setattr(web_search, "search", fake_search)
    uc = _uc(monkeypatch, _FakeAI("bu chaqirilmaydi"))
    text, _ = await _run(uc, "Markaziy bank stavkasi hozir qancha?")
    assert uc.last_outcome == "no_info"
    assert text == NO_INFO_REPLY

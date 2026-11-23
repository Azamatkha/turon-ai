"""Sinov stendi: savol tuzish, javobni hujjat bilan baholash, hisobot."""

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import pytest

from src.evaluation.generator import documents_from_points, parse_cases
from src.evaluation.judge import build_judge_prompt, language_ok
from src.evaluation.runner import run_bench, run_case, summarize
from src.evaluation.schemas import CaseResult, EvalCase


class _Judge:
    """Soxta hakam: navbatdagi JSON'ni qaytaradi, promptlarni yozib boradi."""

    def __init__(self, replies: list[Any]) -> None:
        self.replies = replies
        self.prompts: list[str] = []

    async def generate_json(self, prompt: str, **_: Any) -> Any:
        self.prompts.append(prompt)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return SimpleNamespace(data=reply, usage={})


class _Pipeline:
    def __init__(self, text: str, sources: list[str], verdict: str | None = "ok") -> None:
        self.text = text
        self.sources = sources
        self.last_intent: str | None = "product"
        self.last_outcome = "answered"
        self.last_verdict = verdict

    async def execute_stream(self, question: str, history: Any = None) -> AsyncIterator[dict[str, Any]]:
        yield {"type": "status", "step": "analyze"}
        yield {"type": "delta", "text": self.text}
        yield {"type": "done", "sources": [{"title": t, "score": 0.9} for t in self.sources]}


def _case(style: str = "formal", lang: str = "uz") -> EvalCase:
    return EvalCase("Avtokredit", "Avtokredit foizi qancha?", style, lang, ["22%"])


def test_documents_skip_employees_and_rates() -> None:
    docs = documents_from_points(
        [
            {"title": "Avtokredit", "chunk_index": 1, "chunk_text": "ikkinchi"},
            {"title": "Avtokredit", "chunk_index": 0, "chunk_text": "birinchi"},
            {"title": "Xodimlar", "chunk_index": 0, "chunk_text": "x", "doc_type": "employee"},
            {"title": "Valyuta kursi", "chunk_index": 0, "chunk_text": "k", "rates_json": "{}"},
        ]
    )
    assert docs == {"Avtokredit": "birinchi\nikkinchi"}


def test_parse_cases_adds_cyrillic_and_drops_broken() -> None:
    cases = parse_cases(
        "Avtokredit",
        {
            "questions": [
                {"style": "colloquial", "question": "avtokredit foizi qancha", "expected": ["22%"]},
                {"style": "colloquial", "question": "takror", "expected": []},
                {"style": "absent", "question": "sug'urta narxi?", "expected": ["5%"]},
                {"style": "nonsense", "question": "x", "expected": []},
                {"style": "russian", "question": "", "expected": []},
            ]
        },
    )
    by_style = {c.style: c for c in cases}
    assert set(by_style) == {"colloquial", "absent", "cyrillic"}
    assert by_style["absent"].expected == []
    cyr = by_style["cyrillic"]
    assert cyr.lang == "uz_cyrl" and cyr.expected == ["22%"]
    assert "автокредит" in cyr.question
    assert parse_cases("X", "buzuq") == []


@pytest.mark.parametrize(
    ("answer", "lang", "ok"),
    [
        ("Avtokredit bo'yicha yillik foiz stavkasi 22 foizni tashkil qiladi, muddat 60 oy.", "uz", True),
        ("Ставка по автокредиту составляет 22 процента годовых, срок до 60 месяцев.", "uz", False),
        ("Ставка по автокредиту составляет 22 процента годовых, срок до 60 месяцев.", "ru", True),
        ("Avtokredit bo'yicha yillik foiz stavkasi 22 foizni tashkil qiladi, muddat 60 oy.", "ru", False),
        ("Автокредит бўйича йиллик фоиз ставкаси 22 фоизни ташкил қилади, муддат 60 ой.", "uz_cyrl", True),
        ("22%", "ru", True),  # qisqa javob — alifbo hech narsa aytmaydi
    ],
)
def test_language_ok(answer: str, lang: str, ok: bool) -> None:
    assert language_ok(answer, lang) is ok


def test_judge_prompt_has_document_and_facts() -> None:
    prompt = build_judge_prompt(_case(), "Javob", "Stavka: 22%.")
    assert "Stavka: 22%." in prompt and "- 22%" in prompt and "QUESTION STYLE: formal" in prompt


@pytest.mark.asyncio
async def test_run_case_pass() -> None:
    judge = _Judge([{"passed": True, "failure": "none", "note": "To'g'ri"}])
    r = await run_case(lambda: _Pipeline("Avtokredit foizi 22%.", ["Avtokredit"]), judge, _case(), "Stavka: 22%.")
    assert r.passed and r.failure == "" and r.source_hit
    assert r.intent == "product" and r.pipeline_verdict == "ok"
    assert "Stavka: 22%." in judge.prompts[0]


@pytest.mark.asyncio
async def test_not_found_without_source_is_retrieval_miss() -> None:
    reply = {"passed": False, "failure": "not_found", "note": "Bazada bor edi"}
    r = await run_case(lambda: _Pipeline("Topilmadi.", []), _Judge([dict(reply)]), _case(), "doc")
    assert r.failure == "retrieval_miss"
    # Hujjat topilgan, lekin javobda "yo'q" — bu qidiruv emas, javob xatosi
    r2 = await run_case(lambda: _Pipeline("Topilmadi.", ["Avtokredit"]), _Judge([dict(reply)]), _case(), "doc")
    assert r2.failure == "not_found"


@pytest.mark.asyncio
async def test_wrong_language_skips_judge() -> None:
    judge = _Judge([])
    ru_text = "Ставка по автокредиту составляет 22 процента годовых, срок до 60 месяцев."
    r = await run_case(lambda: _Pipeline(ru_text, ["Avtokredit"]), judge, _case(), "doc")
    assert r.failure == "wrong_language" and judge.prompts == []


@pytest.mark.asyncio
async def test_pipeline_and_judge_errors() -> None:
    class _Broken(_Pipeline):
        async def execute_stream(self, question: str, history: Any = None) -> AsyncIterator[dict[str, Any]]:
            raise RuntimeError("ollama yo'q")
            yield {}

    r = await run_case(lambda: _Broken("", []), _Judge([]), _case(), "doc")
    assert r.failure == "error" and not r.passed
    r2 = await run_case(lambda: _Pipeline("22%", ["Avtokredit"]), _Judge([TimeoutError()]), _case(), "doc")
    assert r2.failure == "error"
    # Noma'lum tur — "incomplete" deb olinadi
    r3 = await run_case(
        lambda: _Pipeline("22%", ["Avtokredit"]),
        _Judge([{"passed": False, "failure": "boshqa", "note": ""}]),
        _case(),
        "doc",
    )
    assert r3.failure == "incomplete"


@pytest.mark.asyncio
async def test_run_bench_progress_and_documents() -> None:
    judge = _Judge([{"passed": True, "failure": "none", "note": ""}] * 2)
    seen: list[tuple[int, int]] = []

    async def progress(i: int, n: int) -> None:
        seen.append((i, n))

    cases = [_case(), EvalCase("Ipoteka", "ipoteka?", "formal", "uz", [])]
    results = await run_bench(
        lambda: _Pipeline("ok", []), judge, cases, {"Avtokredit": "AV-DOC", "Ipoteka": "IP-DOC"}, progress
    )
    assert len(results) == 2 and seen == [(1, 2), (2, 2)]
    assert "AV-DOC" in judge.prompts[0] and "IP-DOC" in judge.prompts[1]


def test_summarize() -> None:
    def res(style: str, passed: bool, failure: str = "", verdict: str | None = "ok") -> CaseResult:
        return CaseResult(_case(style), "a", passed, failure, pipeline_verdict=verdict, latency_ms=100)

    s = summarize(
        [
            res("formal", True),
            res("formal", False, "hallucination"),
            res("typo", False, "retrieval_miss", verdict="fixed"),
            res("typo", False, "error"),
        ]
    )
    assert (s.total, s.passed, s.pass_rate) == (4, 1, 25.0)
    assert s.by_failure == {"hallucination": 1, "retrieval_miss": 1, "error": 1}
    assert s.by_style["formal"].passed == 1 and s.by_style["typo"].total == 2
    # Ichki tekshiruvchi "ok" degan, hakam xato topgan — faqat bittasi
    assert s.verifier_missed == 1
    assert s.avg_latency_ms == 100
    assert summarize([]).pass_rate == 0.0

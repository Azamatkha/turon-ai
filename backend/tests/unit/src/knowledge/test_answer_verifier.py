"""Javob tekshiruvi: rad etilgan javob qayta yoziladi, ikkinchisi ham rad
etilsa — to'qima o'rniga halol "topilmadi"."""

from typing import Any

import pytest

from src.knowledge import usecases as uc_mod
from src.knowledge.prompts import NO_INFO_REPLY
from src.knowledge.usecases import AnswerQuestionUseCase
from src.knowledge.verifier import Verdict, build_verify_prompt


def _use_case(
    monkeypatch: pytest.MonkeyPatch,
    drafts: list[tuple[str, str, str]],
    verdicts: list[Verdict | None],
) -> tuple[AnswerQuestionUseCase, list[str | None]]:
    """drafts: (matn, intent, outcome) — har urinishda bittadan."""
    uc = AnswerQuestionUseCase(embedder=None, store=None, ai_client=None)  # type: ignore[arg-type]
    hints: list[str | None] = []
    routes: list[str | None] = []
    uc._test_routes = routes  # type: ignore[attr-defined]

    async def raw(
        question: str,
        history: Any = None,
        retry_hint: str | None = None,
        retry_route: str | None = None,
    ):
        hints.append(retry_hint)
        routes.append(retry_route)
        text, intent, outcome = drafts.pop(0)
        uc.last_intent = intent
        uc.last_outcome = outcome
        yield {"type": "status", "step": "analyze"}
        yield {"type": "delta", "text": text}
        yield {
            "type": "done",
            "completion_tokens": 5,
            "finish_reason": "stop",
            "max_tokens": 10,
            "sources": [{"title": "x", "score": 1.0}],
        }

    async def verify(*a: Any, **kw: Any) -> Verdict | None:
        return verdicts.pop(0)

    monkeypatch.setattr(uc, "_execute_stream_raw", raw)
    monkeypatch.setattr(uc_mod, "verify_answer", verify)
    monkeypatch.setattr(uc_mod.config.ai, "ANSWER_VERIFY", True)
    return uc, hints


async def _run(uc: AnswerQuestionUseCase) -> tuple[str, list[str], dict[str, Any]]:
    evs = [e async for e in uc.execute_stream("filial ochish rejalari bormi?")]
    text = "".join(e["text"] for e in evs if e["type"] == "delta")
    steps = [e["step"] for e in evs if e["type"] == "status"]
    return text, steps, evs[-1]


@pytest.mark.asyncio
async def test_ok_answer_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    uc, hints = _use_case(
        monkeypatch, [("Javob", "product", "answered")], [Verdict(True, "", 3)]
    )
    text, steps, done = await _run(uc)
    assert text == "Javob"
    assert steps == ["analyze", "verify"]
    assert uc.last_verdict == "ok"
    assert done["completion_tokens"] == 8
    assert hints == [None]


@pytest.mark.asyncio
async def test_rejected_answer_is_rewritten_with_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    uc, hints = _use_case(
        monkeypatch,
        [("1. A filial 2. B filial", "branch", "answered"), ("Rejalar", "product", "answered")],
        [Verdict(False, "asked about plans, got a list", 1), Verdict(True, "", 1)],
    )
    text, steps, _ = await _run(uc)
    # Rad etilgan javob foydalanuvchiga UMUMAN chiqmaydi
    assert text == "Rejalar"
    assert "rewrite" in steps
    assert hints == [None, "asked about plans, got a list"]
    assert uc.last_verdict == "fixed"


@pytest.mark.asyncio
async def test_twice_rejected_gives_honest_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    uc, _ = _use_case(
        monkeypatch,
        [("yomon", "product", "answered"), ("yomon2", "product", "answered")],
        [Verdict(False, "p1", 1), Verdict(False, "p2", 1)],
    )
    text, _, done = await _run(uc)
    assert text == NO_INFO_REPLY
    assert done["sources"] == []
    assert uc.last_verdict == "failed"
    assert uc.last_outcome == "no_info"


@pytest.mark.asyncio
async def test_smalltalk_and_no_info_not_verified(monkeypatch: pytest.MonkeyPatch) -> None:
    uc, _ = _use_case(monkeypatch, [("Salom!", "smalltalk", "answered")], [])
    text, steps, _ = await _run(uc)
    assert text == "Salom!" and "verify" not in steps and uc.last_verdict is None

    uc, _ = _use_case(monkeypatch, [("topilmadi", "product", "no_info")], [])
    _, steps, _ = await _run(uc)
    assert "verify" not in steps


@pytest.mark.asyncio
async def test_verifier_failure_does_not_block_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    uc, _ = _use_case(monkeypatch, [("Javob", "product", "answered")], [None])
    text, _, _ = await _run(uc)
    assert text == "Javob"
    assert uc.last_verdict == "unchecked"


def test_verify_prompt_has_context_and_interpretation() -> None:
    p = build_verify_prompt(
        "19", "Meros omonati: 20%", interpreted="Meros omonati", context="BLOK: 20%"
    )
    assert "Meros omonati" in p and "CONTEXT" in p and "DRAFT ANSWER" in p


@pytest.mark.asyncio
async def test_retry_uses_source_named_by_verifier(monkeypatch: pytest.MonkeyPatch) -> None:
    """"Markaziy bank haqida" -> bazadagi "Bank haqida" (Turonbank) javobi rad
    etiladi va qayta yozish UMUMIY BILIM yo'lidan ketadi."""
    uc, _ = _use_case(
        monkeypatch,
        [("Turonbank 1990-yilda...", "concept", "answered"), ("Markaziy bank...", "concept", "answered")],
        [Verdict(False, "asked about the Central Bank, answered about Turonbank", 1, "general_knowledge"), Verdict(True, "", 1)],
    )
    text, _, _ = await _run(uc)
    assert text == "Markaziy bank..."
    assert uc._test_routes == [None, "general_knowledge"]  # type: ignore[attr-defined]

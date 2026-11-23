"""Savollarni botning HAQIQIY yo'lidan o'tkazish va natijani yig'ish.

Javob `execute_stream` orqali olinadi — foydalanuvchi oladigan yo'lning
o'zi (router, qisqa yo'llar, qidiruv, ichki tekshiruvchi va qayta yozish).
Kesh qatlami chetlab o'tiladi: stend har safar haqiqiy javobni o'lchaydi.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
import time
from typing import Any, Protocol

from loggers import get_logger
from src.core.ai.interfaces import BaseAIClient
from src.evaluation.judge import judge_answer, language_ok
from src.evaluation.schemas import CaseResult, EvalCase, EvalSummary, StyleStat

logger = get_logger(__name__)


class AnswerPipeline(Protocol):
    last_intent: str | None
    last_outcome: str
    last_verdict: str | None

    def execute_stream(
        self, question: str, history: Any = None
    ) -> AsyncIterator[dict[str, Any]]: ...


# Har savolga YANGI use case: u so'rov davomidagi holatni (last_*, kesh
# qilingan bo'laklar) o'zida saqlaydi
PipelineFactory = Callable[[], AnswerPipeline]
ProgressHook = Callable[[int, int], Awaitable[None]]


async def _ask(pipeline: AnswerPipeline, question: str) -> tuple[str, list[str]]:
    parts: list[str] = []
    titles: list[str] = []
    async for ev in pipeline.execute_stream(question, None):
        kind = ev.get("type")
        if kind == "delta":
            parts.append(str(ev.get("text", "")))
        elif kind == "done":
            for s in ev.get("sources") or []:
                title = str((s or {}).get("title") or "") if isinstance(s, dict) else ""
                if title and title not in titles:
                    titles.append(title)
    return "".join(parts), titles


async def run_case(
    make_pipeline: PipelineFactory,
    judge_client: BaseAIClient,
    case: EvalCase,
    document: str,
) -> CaseResult:
    pipeline = make_pipeline()
    started = time.monotonic()
    try:
        answer, titles = await _ask(pipeline, case.question)
    except Exception as exc:  # noqa: BLE001 — bitta savol stendni to'xtatmasin
        logger.warning("Stend: javob olinmadi %r: %s", case.question[:120], exc)
        return CaseResult(
            case=case,
            answer="",
            passed=False,
            failure="error",
            note="Javob yo'li xato bilan tugadi.",
            latency_ms=int((time.monotonic() - started) * 1000),
        )
    latency_ms = int((time.monotonic() - started) * 1000)
    source_hit = case.doc_title in titles
    result = CaseResult(
        case=case,
        answer=answer,
        passed=False,
        intent=pipeline.last_intent,
        outcome=pipeline.last_outcome,
        pipeline_verdict=pipeline.last_verdict,
        source_titles=titles,
        source_hit=source_hit,
        latency_ms=latency_ms,
    )
    # Til xatosi — modelsiz, darhol
    if not language_ok(answer, case.lang):
        result.failure = "wrong_language"
        result.note = "Javob savol tilida emas."
        return result

    grade = await judge_answer(judge_client, case, answer, document)
    result.passed = grade.passed
    result.note = grade.note
    result.failure = grade.failure
    # "Topilmadi" + kerakli hujjat manbalarda yo'q => qidiruv topa olmagan.
    # Bu boshqa tuzatish joyi (qidiruv), shuning uchun alohida tur.
    if grade.failure == "not_found" and not source_hit:
        result.failure = "retrieval_miss"
    return result


async def run_bench(
    make_pipeline: PipelineFactory,
    judge_client: BaseAIClient,
    cases: list[EvalCase],
    documents: dict[str, str],
    on_progress: ProgressHook | None = None,
) -> list[CaseResult]:
    """Savollar KETMA-KET o'tkaziladi: GPU jonli foydalanuvchilar bilan
    bo'lishiladi, parallel yuk ularning javobini sekinlashtirardi."""
    results: list[CaseResult] = []
    for i, case in enumerate(cases, 1):
        results.append(
            await run_case(make_pipeline, judge_client, case, documents.get(case.doc_title, ""))
        )
        if on_progress is not None:
            await on_progress(i, len(cases))
    return results


def summarize(results: list[CaseResult]) -> EvalSummary:
    s = EvalSummary(total=len(results))
    latency = 0
    for r in results:
        latency += r.latency_ms
        st = s.by_style.setdefault(r.case.style, StyleStat())
        st.total += 1
        if r.passed:
            s.passed += 1
            st.passed += 1
            continue
        s.by_failure[r.failure] = s.by_failure.get(r.failure, 0) + 1
        if r.pipeline_verdict == "ok" and r.failure != "error":
            s.verifier_missed += 1
    if results:
        s.pass_rate = round(100 * s.passed / len(results), 1)
        s.avg_latency_ms = latency // len(results)
    return s

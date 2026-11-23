"""Sinov stendi usecase'lari: savollar to'plamini tuzish, o'lchovni boshlash
va bajarish, natijalarni ko'rish.

Og'ir ishlar (savol tuzish, o'lchov) Celery worker'da bajariladi — bitta
o'lchov soatlab davom etadi (har savol: bot javobi + hakam).
"""

from collections.abc import Callable
from dataclasses import asdict
from datetime import timedelta
import random
from typing import Any, cast
from uuid import UUID

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from celery_tasks.types import CeleryTask
from loggers import get_logger
from src.core.ai.interfaces import BaseAIClient
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import InstanceNotFoundException, NotAcceptableException
from src.core.redis.dependencies import get_redis_client
from src.core.utils.datetime_utils import get_utc_now
from src.core.vectorstore.qdrant_store import QdrantStore
from src.evaluation.enums import EvalStatus
from src.evaluation.generator import documents_from_points, generate_cases
from src.evaluation.models import EvalResultRow, EvalRun
from src.evaluation.runner import PipelineFactory, run_case, summarize
from src.evaluation.schemas import (
    CaseResult,
    EvalCase,
    EvalResultView,
    EvalRunDetail,
    EvalRunView,
    EvalStatusView,
)

logger = get_logger(__name__)

# Savol tuzish jarayoni bayrog'i (bir vaqtda bittasi)
EVAL_GENERATING_KEY = "eval:generating"
EVAL_GENERATING_TTL = 3 * 3600
# Shuncha vaqt hech bir javob yozilmagan "faol" o'lchov — worker o'lgan
STALE_RUN_AFTER = timedelta(minutes=30)
# Tanlov har safar bir xil bo'lsin (savollar qayta tuzilganda ham o'sha hujjatlar)
_SAMPLE_SEED = 20261123

NO_CASES = "Avval sinov savollarini tuzing"
RUN_ACTIVE = "O'lchov allaqachon ketmoqda"
GENERATING = "Savollar hozir tuzilmoqda"
RUN_NOT_FOUND = "O'lchov topilmadi"

Uow = ApplicationUnitOfWork[RepositoryProtocol]
SessionFactory = async_sessionmaker[AsyncSession]


def _uow(session: AsyncSession) -> Uow:
    return ApplicationUnitOfWork(session)


def pick_documents(docs: dict[str, str], max_docs: int) -> dict[str, str]:
    """Juda qisqa (matnsiz) hujjatlar tashlanadi; ko'p bo'lsa — barqaror tasodifiy
    tanlov (turli turkumlardan aralash tushadi)."""
    usable = sorted(t for t, text in docs.items() if len(text.strip()) >= 200)
    if len(usable) > max_docs:
        usable = sorted(random.Random(_SAMPLE_SEED).sample(usable, max_docs))
    return {t: docs[t] for t in usable}


def run_view(run: EvalRun, prev: EvalRun | None = None) -> EvalRunView:
    return EvalRunView(
        id=run.id,
        status=run.status,
        total=run.total,
        done=run.done,
        passed=run.passed,
        pass_rate=run.pass_rate,
        prev_pass_rate=prev.pass_rate if prev is not None else None,
        summary=run.summary,
        error=run.error,
        created_at=run.created_at,
        finished_at=run.finished_at,
    )


def _result_row(run_id: UUID, case_id: UUID | None, r: CaseResult) -> dict[str, Any]:
    c = r.case
    return {
        "run_id": run_id,
        "case_id": case_id,
        "doc_title": c.doc_title[:300],
        "question": c.question,
        "style": c.style,
        "lang": c.lang,
        "expected": c.expected,
        "answer": r.answer,
        "passed": r.passed,
        "failure": r.failure,
        "note": r.note,
        "intent": (r.intent or None) and str(r.intent)[:30],
        "outcome": (r.outcome or None) and str(r.outcome)[:20],
        "pipeline_verdict": r.pipeline_verdict,
        "source_titles": r.source_titles[:20],
        "source_hit": r.source_hit,
        "latency_ms": r.latency_ms,
    }


def _case_result(row: EvalResultRow) -> CaseResult:
    """Saqlangan natija -> hisobot uchun (summarize)."""
    return CaseResult(
        case=EvalCase(row.doc_title, row.question, row.style, row.lang, list(row.expected or [])),
        answer=row.answer,
        passed=row.passed,
        failure=row.failure,
        pipeline_verdict=row.pipeline_verdict,
        latency_ms=row.latency_ms,
    )


# ---- Celery tarafida bajariladigan ishlar ----


class GenerateEvalCasesUseCase:
    def __init__(
        self, sessions: SessionFactory, store: QdrantStore, ai_client: BaseAIClient
    ) -> None:
        self.sessions = sessions
        self.store = store
        self.ai_client = ai_client

    async def execute(self, max_docs: int) -> int:
        docs = pick_documents(
            documents_from_points(await self.store.scroll_all_pages()), max_docs
        )
        rows: list[dict[str, Any]] = []
        for title, text in docs.items():
            for c in await generate_cases(self.ai_client, title, text):
                rows.append(
                    {
                        "doc_title": c.doc_title[:300],
                        "question": c.question,
                        "style": c.style,
                        "lang": c.lang,
                        "expected": c.expected,
                    }
                )
        # Model umuman ishlamagan bo'lsa — eski to'plam saqlanib qoladi
        if not rows:
            logger.warning("Stend: birorta ham savol tuzilmadi (%d hujjat)", len(docs))
            return 0
        async with self.sessions() as session, _uow(session) as uow:
            await uow.eval_cases.replace_all(uow.session, rows)
            await uow.commit()
        logger.info("Stend: %d hujjatdan %d savol tuzildi", len(docs), len(rows))
        return len(rows)


class ExecuteEvalRunUseCase:
    """O'lchovni bajaradi. Har javob darhol yoziladi: admin jarayonni ko'radi,
    worker qayta ishga tushsa (acks_late) bajarilgan savollar takrorlanmaydi."""

    def __init__(
        self,
        sessions: SessionFactory,
        store: QdrantStore,
        make_pipeline: PipelineFactory,
        judge_client: BaseAIClient,
    ) -> None:
        self.sessions = sessions
        self.store = store
        self.make_pipeline = make_pipeline
        self.judge_client = judge_client

    async def execute(self, run_id: UUID) -> str:
        async with self.sessions() as session, _uow(session) as uow:
            run = await uow.eval_runs.get_single(uow.session, id=run_id)
            if run is None or run.status not in (EvalStatus.QUEUED, EvalStatus.RUNNING):
                return "skipped"
            cases = await uow.eval_cases.list_all(uow.session)
            done_ids = await uow.eval_results.done_case_ids(uow.session, run_id)
            run.status = EvalStatus.RUNNING.value
            await uow.commit()

        try:
            documents = documents_from_points(await self.store.scroll_all_pages())
            for row in cases:
                if row.id in done_ids:
                    continue
                case = EvalCase(row.doc_title, row.question, row.style, row.lang, list(row.expected or []))
                result = await run_case(
                    self.make_pipeline,
                    self.judge_client,
                    case,
                    documents.get(row.doc_title, ""),
                )
                await self._save(run_id, row.id, result)
            await self._finish(run_id)
        except Exception as exc:
            logger.exception("Stend o'lchovi yiqildi: %s", run_id)
            await self._fail(run_id, str(exc)[:500])
            return "failed"
        return "done"

    async def _save(self, run_id: UUID, case_id: UUID, result: CaseResult) -> None:
        async with self.sessions() as session, _uow(session) as uow:
            await uow.eval_results.create(uow.session, _result_row(run_id, case_id, result))
            run = await uow.eval_runs.get_single(uow.session, id=run_id)
            if run is not None:
                run.done += 1
                run.passed += int(result.passed)
            await uow.commit()

    async def _finish(self, run_id: UUID) -> None:
        async with self.sessions() as session, _uow(session) as uow:
            rows = await uow.eval_results.list_for_run(uow.session, run_id)
            summary = summarize([_case_result(r) for r in rows])
            run = await uow.eval_runs.get_single(uow.session, id=run_id)
            if run is not None:
                run.status = EvalStatus.DONE.value
                run.done = summary.total
                run.passed = summary.passed
                run.pass_rate = summary.pass_rate
                run.summary = asdict(summary)
                run.finished_at = get_utc_now()
            await uow.commit()

    async def _fail(self, run_id: UUID, error: str) -> None:
        async with self.sessions() as session, _uow(session) as uow:
            await uow.eval_runs.update(
                uow.session,
                {"status": EvalStatus.FAILED.value, "error": error, "finished_at": get_utc_now()},
                id=run_id,
            )
            await uow.commit()


# ---- HTTP tarafidagi usecase'lar ----


class StartEvalGenerationUseCase:
    def __init__(self, uow: Uow, redis: Redis, enqueue: Callable[[int], None]) -> None:
        self.uow = uow
        self.redis = redis
        self.enqueue = enqueue

    async def execute(self, max_docs: int) -> None:
        async with self.uow as uow:
            active = await _active_run(uow)
            await uow.commit()
        if active:
            raise NotAcceptableException(RUN_ACTIVE)
        if await self.redis.exists(EVAL_GENERATING_KEY):
            raise NotAcceptableException(GENERATING)
        self.enqueue(max_docs)


class StartEvalRunUseCase:
    def __init__(self, uow: Uow, redis: Redis, enqueue: Callable[[UUID], None]) -> None:
        self.uow = uow
        self.redis = redis
        self.enqueue = enqueue

    async def execute(self, user_id: UUID | None) -> EvalRunView:
        if await self.redis.exists(EVAL_GENERATING_KEY):
            raise NotAcceptableException(GENERATING)
        async with self.uow as uow:
            if await _active_run(uow):
                raise NotAcceptableException(RUN_ACTIVE)
            total = await uow.eval_cases.count(uow.session)
            if total == 0:
                raise NotAcceptableException(NO_CASES)
            run = await uow.eval_runs.create(
                uow.session,
                {"status": EvalStatus.QUEUED.value, "total": total, "started_by": user_id},
            )
            await uow.session.flush()
            view = run_view(run)
            await uow.commit()
        self.enqueue(view.id)
        return view


async def _active_run(uow: Uow) -> EvalRun | None:
    """Faol o'lchov. Uzoq vaqt jim turgani (worker o'lgan) — "failed" qilinadi,
    aks holda yangi o'lchovni hech qachon boshlab bo'lmasdi."""
    now = get_utc_now()
    alive: EvalRun | None = None
    for run in await uow.eval_runs.active(uow.session):
        if now - run.updated_at > STALE_RUN_AFTER:
            run.status = EvalStatus.FAILED.value
            run.error = "Worker javob bermay qoldi"
            run.finished_at = now
        else:
            alive = run
    await uow.session.flush()
    return alive


class EvalStatusUseCase:
    def __init__(self, uow: Uow, redis: Redis) -> None:
        self.uow = uow
        self.redis = redis

    async def execute(self) -> EvalStatusView:
        async with self.uow as uow:
            by_style = await uow.eval_cases.count_by_style(uow.session)
            active = await _active_run(uow)
            view = EvalStatusView(
                cases=sum(by_style.values()),
                by_style=by_style,
                generating=bool(await self.redis.exists(EVAL_GENERATING_KEY)),
                active_run=run_view(active) if active else None,
            )
            await uow.commit()
        return view


class ListEvalRunsUseCase:
    def __init__(self, uow: Uow) -> None:
        self.uow = uow

    async def execute(self) -> list[EvalRunView]:
        async with self.uow as uow:
            runs = await uow.eval_runs.list_recent(uow.session)
        # Har o'lchov uchun oldingi TUGAGAN o'lchov foizi (ro'yxat yangidan eskiga)
        views: list[EvalRunView] = []
        for i, run in enumerate(runs):
            prev = next((r for r in runs[i + 1 :] if r.status == EvalStatus.DONE), None)
            views.append(run_view(run, prev))
        return views


class GetEvalRunUseCase:
    def __init__(self, uow: Uow) -> None:
        self.uow = uow

    async def execute(self, run_id: UUID, failed_only: bool) -> EvalRunDetail:
        async with self.uow as uow:
            run = await uow.eval_runs.get_single(uow.session, id=run_id)
            if run is None:
                raise InstanceNotFoundException(RUN_NOT_FOUND)
            prev = await uow.eval_runs.previous_done(uow.session, run)
            rows = await uow.eval_results.list_for_run(uow.session, run_id, failed_only)
        base = run_view(run, prev)
        return EvalRunDetail(
            **base.model_dump(),
            results=[EvalResultView.model_validate(r) for r in rows],
        )


# ---- DI ----


def _enqueue_generation(max_docs: int) -> None:
    from src.evaluation.tasks import generate_eval_cases

    cast(CeleryTask, generate_eval_cases).delay(max_docs=max_docs)


def _enqueue_run(run_id: UUID) -> None:
    from src.evaluation.tasks import run_eval

    cast(CeleryTask, run_eval).delay(run_id=str(run_id))


def get_start_eval_generation_use_case(
    uow: Uow = Depends(get_unit_of_work), redis: Redis = Depends(get_redis_client)
) -> StartEvalGenerationUseCase:
    return StartEvalGenerationUseCase(uow, redis, _enqueue_generation)


def get_start_eval_run_use_case(
    uow: Uow = Depends(get_unit_of_work), redis: Redis = Depends(get_redis_client)
) -> StartEvalRunUseCase:
    return StartEvalRunUseCase(uow, redis, _enqueue_run)


def get_eval_status_use_case(
    uow: Uow = Depends(get_unit_of_work), redis: Redis = Depends(get_redis_client)
) -> EvalStatusUseCase:
    return EvalStatusUseCase(uow, redis)


def get_list_eval_runs_use_case(uow: Uow = Depends(get_unit_of_work)) -> ListEvalRunsUseCase:
    return ListEvalRunsUseCase(uow)


def get_eval_run_use_case(uow: Uow = Depends(get_unit_of_work)) -> GetEvalRunUseCase:
    return GetEvalRunUseCase(uow)

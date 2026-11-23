"""Stend usecase'lari: hujjat tanlash, o'lchovni bajarish (davom ettirish bilan),
faol o'lchov tekshiruvi."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.core.errors.exceptions import NotAcceptableException
from src.core.utils.datetime_utils import get_utc_now
from src.evaluation import usecases as uc


class _Runs:
    def __init__(self, runs: list[Any]) -> None:
        self.runs = runs

    async def get_single(self, session: Any, id: UUID) -> Any:
        return next((r for r in self.runs if r.id == id), None)

    async def active(self, session: Any) -> list[Any]:
        return [r for r in self.runs if r.status in ("queued", "running")]

    async def create(self, session: Any, data: dict[str, Any]) -> Any:
        run = SimpleNamespace(
            id=uuid4(), done=0, passed=0, pass_rate=None, summary=None, error="",
            created_at=get_utc_now(), updated_at=get_utc_now(), finished_at=None, **data,
        )
        self.runs.append(run)
        return run

    async def update(self, session: Any, data: dict[str, Any], id: UUID) -> None:
        run = await self.get_single(session, id)
        for k, v in data.items():
            setattr(run, k, v)


class _Cases:
    def __init__(self, cases: list[Any]) -> None:
        self.cases = cases

    async def list_all(self, session: Any) -> list[Any]:
        return self.cases

    async def count(self, session: Any) -> int:
        return len(self.cases)


class _Results:
    def __init__(self) -> None:
        self.rows: list[Any] = []

    async def create(self, session: Any, data: dict[str, Any]) -> None:
        self.rows.append(SimpleNamespace(**data))

    async def done_case_ids(self, session: Any, run_id: UUID) -> set[UUID]:
        return {r.case_id for r in self.rows if r.run_id == run_id}

    async def list_for_run(self, session: Any, run_id: UUID, failed_only: bool = False) -> list[Any]:
        return [r for r in self.rows if r.run_id == run_id]


class _Uow:
    def __init__(self, db: SimpleNamespace) -> None:
        self.session = SimpleNamespace(flush=self._noop)
        self.eval_runs = db.runs
        self.eval_cases = db.cases
        self.eval_results = db.results
        self.commits = 0

    async def _noop(self) -> None:
        return None

    async def __aenter__(self) -> "_Uow":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1


def _db(runs: list[Any], cases: list[Any]) -> SimpleNamespace:
    return SimpleNamespace(runs=_Runs(runs), cases=_Cases(cases), results=_Results())


def _sessions() -> Any:
    @asynccontextmanager
    async def factory() -> AsyncIterator[None]:
        yield None

    return factory


def _case(title: str, style: str = "formal") -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), doc_title=title, question=f"{title}?", style=style, lang="uz", expected=["1%"])


class _Store:
    async def scroll_all_pages(self) -> list[dict[str, Any]]:
        return [
            {"title": "A", "chunk_index": 0, "chunk_text": "A hujjat 1%"},
            {"title": "B", "chunk_index": 0, "chunk_text": "B hujjat 1%"},
        ]


class _Pipeline:
    last_intent = "product"
    last_outcome = "answered"
    last_verdict = "ok"

    async def execute_stream(self, question: str, history: Any = None) -> AsyncIterator[dict[str, Any]]:
        yield {"type": "delta", "text": "1%"}
        yield {"type": "done", "sources": [{"title": question.rstrip("?")}]}


class _Judge:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def generate_json(self, prompt: str, **_: Any) -> Any:
        self.prompts.append(prompt)
        passed = "A hujjat" in prompt
        return SimpleNamespace(data={"passed": passed, "failure": "incomplete", "note": "-"}, usage={})


def test_pick_documents_skips_short_and_is_stable() -> None:
    docs = {f"D{i:02d}": "x" * 300 for i in range(50)}
    docs["qisqa"] = "x"
    picked = uc.pick_documents(docs, 10)
    assert len(picked) == 10 and "qisqa" not in picked
    assert picked == uc.pick_documents(docs, 10)
    assert len(uc.pick_documents(docs, 100)) == 50


@pytest.mark.asyncio
async def test_execute_run_saves_each_result_and_resumes(monkeypatch: pytest.MonkeyPatch) -> None:
    cases = [_case("A"), _case("B")]
    run = SimpleNamespace(
        id=uuid4(), status="queued", total=2, done=0, passed=0, pass_rate=None, summary=None,
        error="", finished_at=None,
    )
    db = _db([run], cases)
    # Worker qayta ishga tushgan: A allaqachon baholangan
    db.results.rows.append(
        SimpleNamespace(
            run_id=run.id, case_id=cases[0].id, doc_title="A", question="A?", style="formal",
            lang="uz", expected=[], answer="1%", passed=True, failure="", pipeline_verdict="ok",
            latency_ms=10,
        )
    )
    run.done, run.passed = 1, 1
    monkeypatch.setattr(uc, "_uow", lambda session: _Uow(db))
    judge = _Judge()

    out = await uc.ExecuteEvalRunUseCase(_sessions(), _Store(), lambda: _Pipeline(), judge).execute(run.id)  # type: ignore[arg-type]
    assert out == "done"
    # Faqat B so'raldi, uning hakamiga B hujjati berildi
    assert len(judge.prompts) == 1 and "B hujjat" in judge.prompts[0]
    assert run.status == "done" and run.done == 2 and run.passed == 1
    assert run.pass_rate == 50.0 and run.summary["by_failure"] == {"incomplete": 1}
    assert run.finished_at is not None
    saved = db.results.rows[-1]
    assert saved.case_id == cases[1].id and saved.source_hit is True


@pytest.mark.asyncio
async def test_execute_run_skips_finished_and_marks_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    done_run = SimpleNamespace(id=uuid4(), status="done")
    db = _db([done_run], [_case("A")])
    monkeypatch.setattr(uc, "_uow", lambda session: _Uow(db))
    out = await uc.ExecuteEvalRunUseCase(_sessions(), _Store(), lambda: _Pipeline(), _Judge()).execute(done_run.id)  # type: ignore[arg-type]
    assert out == "skipped"

    class _BrokenStore:
        async def scroll_all_pages(self) -> list[dict[str, Any]]:
            raise RuntimeError("qdrant yo'q")

    run = SimpleNamespace(id=uuid4(), status="queued", error="", finished_at=None)
    db2 = _db([run], [_case("A")])
    monkeypatch.setattr(uc, "_uow", lambda session: _Uow(db2))
    out = await uc.ExecuteEvalRunUseCase(_sessions(), _BrokenStore(), lambda: _Pipeline(), _Judge()).execute(run.id)  # type: ignore[arg-type]
    assert out == "failed" and run.status == "failed" and "qdrant" in run.error


class _Redis:
    def __init__(self, generating: bool = False) -> None:
        self.generating = generating

    async def exists(self, key: str) -> int:
        return int(self.generating)


@pytest.mark.asyncio
async def test_start_run_rules() -> None:
    queued: list[UUID] = []

    # Savol yo'q
    with pytest.raises(NotAcceptableException):
        await uc.StartEvalRunUseCase(_Uow(_db([], [])), _Redis(), queued.append).execute(None)  # type: ignore[arg-type]
    # Savollar tuzilmoqda
    with pytest.raises(NotAcceptableException):
        await uc.StartEvalRunUseCase(_Uow(_db([], [_case("A")])), _Redis(True), queued.append).execute(None)  # type: ignore[arg-type]

    # Jim qolgan (worker o'lgan) o'lchov yangisiga to'sqinlik qilmaydi
    stale = SimpleNamespace(
        id=uuid4(), status="running", updated_at=get_utc_now() - timedelta(hours=2),
        error="", finished_at=None,
    )
    db = _db([stale], [_case("A"), _case("B")])
    view = await uc.StartEvalRunUseCase(_Uow(db), _Redis(), queued.append).execute(None)  # type: ignore[arg-type]
    assert stale.status == "failed"
    assert view.status == "queued" and view.total == 2 and queued == [view.id]

    # Endi faol o'lchov bor — ikkinchisi boshlanmaydi
    with pytest.raises(NotAcceptableException):
        await uc.StartEvalRunUseCase(_Uow(db), _Redis(), queued.append).execute(None)  # type: ignore[arg-type]

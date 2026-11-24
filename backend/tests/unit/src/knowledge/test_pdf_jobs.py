"""PDF fonda: ish holati Redis'da, sahifa bo'yicha progress, xato va jim
qolgan ish."""

from datetime import timedelta
from typing import Any

import pytest

from src.core.errors.exceptions import InstanceProcessingException
from src.core.utils.datetime_utils import get_utc_now
from src.knowledge import pdf_jobs
from src.knowledge.pdf_jobs import PdfJobStore, run_pdf_job
from src.knowledge.schemas import PdfUploadResult
from tests.fakes.redis import InMemoryRedis


class _Redis(InMemoryRedis):
    """Sorted set'ning stendga kerakli qismi."""

    def __init__(self) -> None:
        super().__init__()
        self.z: dict[str, float] = {}

    async def zadd(self, key: str, mapping: dict[str, float]) -> int:
        self.z.update(mapping)
        return len(mapping)

    async def zrevrange(self, key: str, start: int, end: int) -> list[str]:
        ids = sorted(self.z, key=lambda k: self.z[k], reverse=True)
        return ids[start : end + 1]

    async def zrem(self, key: str, *ids: str) -> int:
        for i in ids:
            self.z.pop(i, None)
        return len(ids)

    async def zremrangebyrank(self, key: str, start: int, end: int) -> int:
        return 0


def _result(title: str = "Kredit nizomi") -> PdfUploadResult:
    return PdfUploadResult(
        chunks=3, vector_dim=1024, total_points=10, title=title, pages=2,
        ocr_pages=0, vision_pages=2, chars=500,
    )


class _UseCase:
    def __init__(self, fail: Exception | None = None) -> None:
        self.fail = fail
        self.seen: list[tuple[str, int, int]] = []

    async def execute(self, file_bytes: bytes, filename: str, title: str = "", progress: Any = None) -> PdfUploadResult:
        for i in range(2):
            await progress("reading", i, 2)
        if self.fail:
            raise self.fail
        await progress("saving", 0, 0)
        return _result()


@pytest.mark.asyncio
async def test_job_runs_and_reports_progress() -> None:
    jobs = PdfJobStore(_Redis())  # type: ignore[arg-type]
    job = await jobs.create("1308.pdf", "")
    assert job.status == "queued"
    done: list[str] = []

    async def on_done(r: PdfUploadResult) -> None:
        done.append(r.title)

    await run_pdf_job(jobs, job.id, _UseCase(), b"%PDF", "1308.pdf", "", on_done)  # type: ignore[arg-type]
    final = await jobs.get(job.id)
    assert final is not None and final.status == "done"
    assert final.result is not None and final.title == "Kredit nizomi"
    assert done == ["Kredit nizomi"]
    assert [j.id for j in await jobs.recent()] == [job.id]


@pytest.mark.asyncio
async def test_progress_is_visible_while_running() -> None:
    jobs = PdfJobStore(_Redis())  # type: ignore[arg-type]
    job = await jobs.create("a.pdf", "")
    snapshots: list[tuple[str, str, int, int]] = []

    class _Watching(_UseCase):
        async def execute(self, file_bytes: bytes, filename: str, title: str = "", progress: Any = None) -> PdfUploadResult:
            await progress("reading", 1, 9)
            cur = await jobs.get(job.id)
            assert cur is not None
            snapshots.append((cur.status, cur.stage, cur.done, cur.total))
            return _result()

    async def on_done(r: PdfUploadResult) -> None:
        return None

    await run_pdf_job(jobs, job.id, _Watching(), b"", "a.pdf", "", on_done)  # type: ignore[arg-type]
    assert snapshots == [("running", "reading", 1, 9)]


@pytest.mark.asyncio
async def test_failure_messages() -> None:
    jobs = PdfJobStore(_Redis())  # type: ignore[arg-type]

    async def on_done(r: PdfUploadResult) -> None:
        raise AssertionError("xatoda bildirishnoma yo'q")

    job = await jobs.create("a.pdf", "")
    business = InstanceProcessingException("PDF'dan matn ajratib bo'lmadi")
    await run_pdf_job(jobs, job.id, _UseCase(business), b"", "a.pdf", "", on_done)  # type: ignore[arg-type]
    failed = await jobs.get(job.id)
    assert failed is not None and failed.status == "failed"
    assert failed.error == "PDF'dan matn ajratib bo'lmadi"

    # Infratuzilma xatosi — ichki tafsilot (manzil) ko'rsatilmaydi
    job2 = await jobs.create("b.pdf", "")
    await run_pdf_job(jobs, job2.id, _UseCase(RuntimeError("http://10.0.0.5:11434 down")), b"", "b.pdf", "", on_done)  # type: ignore[arg-type]
    failed2 = await jobs.get(job2.id)
    assert failed2 is not None and failed2.error == pdf_jobs.FAILED_ERROR


@pytest.mark.asyncio
async def test_stale_running_job_becomes_failed() -> None:
    jobs = PdfJobStore(_Redis())  # type: ignore[arg-type]
    job = await jobs.create("a.pdf", "")
    old = get_utc_now() - timedelta(seconds=pdf_jobs.STALE_AFTER_SECONDS + 5)
    await jobs._save(job.model_copy(update={"status": "running", "updated_at": old}))
    got = await jobs.get(job.id)
    assert got is not None and got.status == "failed" and got.error == pdf_jobs.STALE_ERROR
    assert await jobs.get("yoq") is None

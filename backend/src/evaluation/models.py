from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base import Base
from src.core.database.mixins import TimestampMixin, UUIDIDMixin


class EvalCaseRow(Base, UUIDIDMixin, TimestampMixin):
    """Stend savoli — bir marta tuziladi, har o'lchovda AYNAN shular beriladi."""

    __tablename__ = "eval_cases"

    doc_title: Mapped[str] = mapped_column(String(300))
    question: Mapped[str] = mapped_column(Text)
    style: Mapped[str] = mapped_column(String(20))
    lang: Mapped[str] = mapped_column(String(10))
    expected: Mapped[list[str]] = mapped_column(JSONB, default=list)


class EvalRun(Base, UUIDIDMixin, TimestampMixin):
    """Bitta o'lchov. Har javob tayyor bo'lishi bilan `done`/`passed` yangilanadi
    — admin jarayonni kuzatib turadi, worker qayta ishga tushsa davom etadi."""

    __tablename__ = "eval_runs"

    # EvalStatus: queued | running | done | failed
    status: Mapped[str] = mapped_column(String(16), index=True)
    total: Mapped[int] = mapped_column(Integer, default=0)
    done: Mapped[int] = mapped_column(Integer, default=0)
    passed: Mapped[int] = mapped_column(Integer, default=0)
    pass_rate: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    # EvalSummary (asdict) — tugagach
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, default=None)
    error: Mapped[str] = mapped_column(Text, default="")
    started_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )


class EvalResultRow(Base, UUIDIDMixin, TimestampMixin):
    """Bitta savol natijasi. Savol matni nusxalanadi: savollar qayta tuzilsa
    ham eski o'lchovlar o'qiladigan qoladi."""

    __tablename__ = "eval_results"

    run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("eval_runs.id", ondelete="CASCADE"),
        index=True,
    )
    case_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("eval_cases.id", ondelete="SET NULL"),
        nullable=True,
    )
    doc_title: Mapped[str] = mapped_column(String(300))
    question: Mapped[str] = mapped_column(Text)
    style: Mapped[str] = mapped_column(String(20))
    lang: Mapped[str] = mapped_column(String(10))
    expected: Mapped[list[str]] = mapped_column(JSONB, default=list)
    answer: Mapped[str] = mapped_column(Text, default="")
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    failure: Mapped[str] = mapped_column(String(20), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    intent: Mapped[str | None] = mapped_column(String(30), nullable=True, default=None)
    outcome: Mapped[str | None] = mapped_column(String(20), nullable=True, default=None)
    pipeline_verdict: Mapped[str | None] = mapped_column(String(16), nullable=True, default=None)
    source_titles: Mapped[list[str]] = mapped_column(JSONB, default=list)
    source_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)

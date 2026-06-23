from typing import Any

from src.core.schemas import Base


class AttemptInfo(Base):
    model: str
    attempt: int
    ok: bool
    status: int | None = None
    error_type: str | None = None


class DiagnosticResponse(Base):
    ok: bool
    latency_ms: int
    used_model: str
    fallback_used: bool
    total_attempts: int
    model_chain: list[str]
    attempts: list[AttemptInfo]
    response: dict[str, Any] | None = None


class CallResult(Base):
    data: Any
    used_model: str
    fallback_used: bool
    total_attempts: int
    usage: dict[str, Any] = {}
    model: str = ""
    model_chain: list[str] = []
    attempts: list[AttemptInfo] = []

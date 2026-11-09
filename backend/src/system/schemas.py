from typing import Literal

from src.core.schemas import Base


class HealthCheckResponse(Base):
    status: Literal["ok"] = "ok"


class ReadyResponse(Base):
    """Ommaviy readiness javobi — faqat ishlaydi/ishlamaydi, tafsilotsiz
    (ichki xost nomlari va xato matnlari tashqariga chiqmasin)."""

    # "ok" | "degraded" | "down"
    status: str
    components: dict[str, bool]


class ComponentStatusView(Base):
    name: str
    ok: bool
    latency_ms: int
    critical: bool
    detail: str = ""

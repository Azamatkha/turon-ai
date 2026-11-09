from datetime import datetime
from typing import Any
from uuid import UUID

from src.core.schemas import Base


class AuditLogView(Base):
    id: UUID
    created_at: datetime
    actor_id: UUID | None = None
    actor_username: str
    action: str
    target_type: str
    target_id: str | None = None
    target_label: str | None = None
    details: dict[str, Any] | None = None
    ip: str | None = None


class AuditLogPageView(Base):
    items: list[AuditLogView]
    total: int

from datetime import datetime
from uuid import UUID

from src.core.schemas import Base


class NotificationView(Base):
    id: UUID
    type: str
    params: dict[str, str]
    is_read: bool
    created_at: datetime
    entity_id: UUID | None = None


class NotificationListView(Base):
    items: list[NotificationView]
    unread_count: int
    total: int


class UnreadCountView(Base):
    count: int

from datetime import datetime
from typing import Any
from uuid import UUID

from src.core.schemas import Base


class DeptStat(Base):
    name: str
    count: int
    pct: int


class WeeklyPoint(Base):
    label: str
    count: int


class TopUserStat(Base):
    name: str
    username: str
    department: str | None
    count: int


class RecentActivityItem(Base):
    name: str
    action: str
    when: datetime


class DashboardStatsView(Base):
    total_users: int
    total_sessions: int
    total_messages: int
    total_departments: int
    online: int
    total_likes: int
    total_dislikes: int
    departments: list[DeptStat]
    # Filtr uchun: BARCHA foydalanuvchilarning bo'limlari. `departments` faqat
    # so'rov yuborganlarni sanaydi — filtrda esa hali chatdan foydalanmagan
    # foydalanuvchining bo'limi ham ko'rinishi kerak.
    all_departments: list[str] = []
    weekly: list[WeeklyPoint]
    recent_activity: list[RecentActivityItem]
    # So'nggi 30 kunda eng ko'p savol bergan 5 xodim (dashboard diagrammasi)
    top_users: list[TopUserStat] = []


class FaceIdLogView(Base):
    """`/auth/save` ga kelgan bitta GSI signature (test/tahlil uchun)."""

    id: UUID
    created_at: datetime
    # "ok" | "not_employee" | xato sababi
    result: str
    # User topilmagan bo'lsa (masalan tokenda verificationId yo'q) — None
    username: str | None = None
    request_id: str | None = None
    # Kelgan xom JWT
    signature: str
    # Decode qilingan claim'lar (`body` ochilgan holda)
    claims: dict[str, Any] | None = None
    # --- signature ichidan ajratib olingan qisqa ma'lumot (tekshirilmagan) ---
    person_name: str | None = None
    pnfl: str | None = None
    document: str | None = None
    birth_date: str | None = None
    # signature ichida bizning accessToken bormi
    has_token: bool = False
    # Tokendagi `sub` (user_id) va `verificationId`; yo'q bo'lsa None
    token_sub: str | None = None
    verification_id: str | None = None


class FaceIdLogPageView(Base):
    items: list[FaceIdLogView]
    total: int

from datetime import datetime
from typing import Any
from uuid import UUID

from src.core.schemas import Base
from src.system.schemas import ComponentStatusView


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


class DislikedAnswerView(Base):
    """Dislike olgan bitta bot javobi — admin ko'rib chiqishi uchun."""

    id: UUID
    session_id: UUID
    created_at: datetime
    question: str | None = None
    answer: str
    # [{"title": ..., "score": ...}] — javob tayangan hujjatlar
    sources: list[dict[str, Any]] | None = None
    reason: str | None = None
    comment: str | None = None
    reviewed: bool = False
    user_name: str
    username: str
    session_title: str = ""


class DislikedAnswerPageView(Base):
    items: list[DislikedAnswerView]
    total: int


class ReviewDislikedModel(Base):
    reviewed: bool = True


class QuestionStatItem(Base):
    """Bir xil savollar guruhi."""

    question: str
    count: int
    users: int
    last_asked: datetime


class QuestionSummary(Base):
    total: int
    no_info: int
    errors: int
    # O'rtacha javob vaqti (ms) va jami token — LLM yuklamasini kuzatish uchun
    avg_duration_ms: int
    total_tokens: int


class QuestionAnalyticsView(Base):
    days: int
    summary: QuestionSummary
    top: list[QuestionStatItem]
    unanswered: list[QuestionStatItem]


class HourlyPoint(Base):
    hour: datetime
    questions: int
    errors: int
    no_info: int
    avg_ms: int


class LlmMetrics(Base):
    """So'nggi `hours` soatdagi bot ishlashi (question_logs'dan)."""

    hours: int
    questions: int
    errors: int
    no_info: int
    tokens: int
    p50_ms: int
    p95_ms: int
    max_ms: int
    hourly: list[HourlyPoint]
    # Javob keshi — bugun (Toshkent): keshdan berilgan / modeldan olib keshlangan
    cache_hits_today: int = 0
    cache_misses_today: int = 0


class SystemStatusView(Base):
    # "ok" | "degraded" | "down"
    status: str
    checked_at: datetime
    components: list[ComponentStatusView]
    llm: LlmMetrics


class FlaggedQuestionView(Base):
    id: UUID
    created_at: datetime
    # "harmful" — noqonuniy/xavfli (router), "profanity" — so'kinish (lug'at)
    kind: str
    question: str
    username: str | None = None
    user_name: str = ""


class FlaggedQuestionPageView(Base):
    items: list[FlaggedQuestionView]
    total: int


class WebAnswerView(Base):
    """Bazada yo'q, ruxsat etilgan saytdan javob berilgan savol."""

    id: UUID
    created_at: datetime
    question: str
    source_urls: list[str] = []
    username: str | None = None
    user_name: str = ""


class WebAnswerPageView(Base):
    items: list[WebAnswerView]
    total: int

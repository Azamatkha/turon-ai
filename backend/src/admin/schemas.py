from datetime import datetime

from src.core.schemas import Base


class DeptStat(Base):
    name: str
    count: int
    pct: int


class WeeklyPoint(Base):
    label: str
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

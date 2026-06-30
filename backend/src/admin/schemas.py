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
    when: datetime


class DashboardStatsView(Base):
    total_users: int
    total_sessions: int
    total_messages: int
    total_departments: int
    departments: list[DeptStat]
    weekly: list[WeeklyPoint]
    recent_activity: list[RecentActivityItem]

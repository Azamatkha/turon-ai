from datetime import timedelta

from fastapi import Depends

from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.utils.datetime_utils import get_utc_now
from src.admin.schemas import (
    DashboardStatsView,
    DeptStat,
    RecentActivityItem,
    WeeklyPoint,
)

# Hafta kunlari qisqartmalari (Dushanba=0 ... Yakshanba=6)
WEEKDAY_LABELS = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]


class DashboardStatsUseCase:
    """Dashboard uchun real statistika (DB'dan)."""

    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self) -> DashboardStatsView:
        async with self.uow as uow:
            total_users = await uow.users.count(uow.session)
            total_sessions = await uow.chat_sessions.count(uow.session)
            # "Jami so'rovlar" — faqat foydalanuvchi xabarlari (bot javoblari emas)
            total_messages = await uow.chat_messages.count(uow.session, role="user")
            total_departments = len(
                [r for r in await uow.users.count_by_department(uow.session) if r[0]]
            )

            # Bo'lim ulushi — so'rovlar (user xabarlari) bo'yicha
            req_by_dept = await uow.chat_messages.count_requests_by_department(
                uow.session
            )
            total_req = sum(c for _, c in req_by_dept)
            departments: list[DeptStat] = []
            for name, count in req_by_dept:
                pct = round(count / total_req * 100) if total_req else 0
                departments.append(
                    DeptStat(name=name or "Boshqa", count=count, pct=pct)
                )
            departments.sort(key=lambda d: d.count, reverse=True)

            # So'nggi 7 kun: har kun uchun xabarlar soni (eskidan yangiga)
            per_day = await uow.chat_messages.count_per_day(uow.session, days=7)
            today = get_utc_now().date()
            weekly = [
                WeeklyPoint(
                    label=WEEKDAY_LABELS[(d := today - timedelta(days=i)).weekday()],
                    count=per_day.get(d, 0),
                )
                for i in range(6, -1, -1)
            ]

            # Onlayn foydalanuvchilar (oxirgi 5 daqiqada faol)
            online = await uow.users.count_online(uow.session, minutes=5)

            # Like / dislike sanog'i
            total_likes = await uow.chat_messages.count(uow.session, vote="up")
            total_dislikes = await uow.chat_messages.count(uow.session, vote="down")

            # So'nggi faollik — login / logout / suhbat ochish
            events = await uow.login_events.recent_with_users(uow.session, limit=10)
            recent_activity = [
                RecentActivityItem(name=name, action=action, when=when)
                for name, action, when in events
            ]

            return DashboardStatsView(
                total_users=total_users,
                total_sessions=total_sessions,
                total_messages=total_messages,
                total_departments=total_departments,
                online=online,
                total_likes=total_likes,
                total_dislikes=total_dislikes,
                departments=departments,
                weekly=weekly,
                recent_activity=recent_activity,
            )


def get_dashboard_stats_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> DashboardStatsUseCase:
    return DashboardStatsUseCase(uow=uow)

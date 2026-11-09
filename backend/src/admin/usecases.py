from datetime import timedelta
from uuid import UUID

from fastapi import Depends

from src.admin.schemas import (
    ComponentStatusView,
    DashboardStatsView,
    DeptStat,
    DislikedAnswerPageView,
    DislikedAnswerView,
    FaceIdLogPageView,
    FaceIdLogView,
    FlaggedQuestionPageView,
    FlaggedQuestionView,
    HourlyPoint,
    LlmMetrics,
    QuestionAnalyticsView,
    QuestionStatItem,
    QuestionSummary,
    RecentActivityItem,
    SystemStatusView,
    TopUserStat,
    WeeklyPoint,
)
from src.chat.answer_cache import cache_stats_today
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import InstanceNotFoundException
from src.core.utils.datetime_utils import get_utc_now
from src.system.dependencies import get_readiness_service
from src.system.readiness import ReadinessService, overall_status
from src.user.auth.services.gsi_signature import summarize_claims

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
            dept_rows = await uow.users.count_by_department(uow.session)
            total_departments = len([r for r in dept_rows if r[0]])
            # Filtr ro'yxati — foydalanuvchilar bo'yicha (so'rov yubormaganlar ham)
            all_departments = sorted({str(r[0]) for r in dept_rows if r[0]})

            # Bo'lim ulushi — so'rovlar (user xabarlari) bo'yicha
            req_by_dept = await uow.chat_messages.count_requests_by_department(
                uow.session
            )
            # Bo'sh departament va qo'lda "Boshqa" deb yozilgani bitta
            # "Boshqa" qatoriga birlashadi (aks holda diagrammada ikkita
            # "Boshqa" chiqardi)
            merged: dict[str, int] = {}
            for name, count in req_by_dept:
                key = (name or "").strip() or "Boshqa"
                if key.lower() == "boshqa":
                    key = "Boshqa"
                merged[key] = merged.get(key, 0) + count
            total_req = sum(merged.values())
            departments: list[DeptStat] = []
            for name, count in merged.items():
                pct = round(count / total_req * 100) if total_req else 0
                departments.append(DeptStat(name=name, count=count, pct=pct))
            departments.sort(key=lambda d: d.count, reverse=True)

            # So'nggi 7 kun: har kun uchun so'rovlar soni (eskidan yangiga).
            # Faqat foydalanuvchi xabarlari — bot javoblari sanalmaydi.
            per_day = await uow.chat_messages.count_per_day(
                uow.session, days=7, role="user"
            )
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

            # Eng faol xodimlar — so'nggi 30 kun, top-5
            top_rows = await uow.chat_messages.top_users_by_requests(
                uow.session, days=30, limit=5
            )
            top_users = [
                TopUserStat(name=name or username, username=username, department=dept, count=count)
                for name, username, dept, count in top_rows
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
                all_departments=all_departments,
                weekly=weekly,
                recent_activity=recent_activity,
                top_users=top_users,
            )


def get_dashboard_stats_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> DashboardStatsUseCase:
    return DashboardStatsUseCase(uow=uow)


class ListFaceIdLogsUseCase:
    """Kelgan GSI signature'lar ro'yxati (yangisidan eskisiga)."""

    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self, only_failed: bool = False, page: int = 1, size: int = 20
    ) -> FaceIdLogPageView:
        async with self.uow as uow:
            rows, total = await uow.face_id_signature_logs.list_with_usernames(
                uow.session, only_failed=only_failed, page=page, size=size
            )
            return FaceIdLogPageView(
                items=[
                    FaceIdLogView(
                        id=log.id,
                        created_at=log.created_at,
                        result=log.result,
                        username=username,
                        request_id=log.request_id,
                        signature=log.signature,
                        claims=log.claims,
                        **summarize_claims(log.claims),
                    )
                    for log, username in rows
                ],
                total=total,
            )


def get_list_face_id_logs_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> ListFaceIdLogsUseCase:
    return ListFaceIdLogsUseCase(uow=uow)


class ListDislikedAnswersUseCase:
    """Dislike olgan javoblar: savol, javob, manba va user sababi."""

    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self, only_open: bool = True, page: int = 1, size: int = 20
    ) -> DislikedAnswerPageView:
        async with self.uow as uow:
            rows, total = await uow.chat_messages.list_disliked(
                uow.session, only_open=only_open, page=page, size=size
            )
            return DislikedAnswerPageView(
                items=[
                    DislikedAnswerView(
                        id=msg.id,
                        session_id=msg.session_id,
                        created_at=msg.created_at,
                        question=question,
                        answer=msg.content,
                        sources=msg.sources,
                        reason=msg.vote_reason,
                        comment=msg.vote_comment,
                        reviewed=msg.vote_reviewed,
                        user_name=user_name or username,
                        username=username,
                        session_title=title,
                    )
                    for msg, question, title, user_name, username in rows
                ],
                total=total,
            )


class ReviewDislikedAnswerUseCase:
    """Admin yoqmagan javobni "ko'rib chiqildi" (yoki qaytadan ochiq) qiladi."""

    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, message_id: UUID, reviewed: bool) -> None:
        async with self.uow as uow:
            msg = await uow.chat_messages.get_single(
                uow.session, id=message_id, vote="down"
            )
            if not msg:
                raise InstanceNotFoundException("Xabar topilmadi")
            msg.vote_reviewed = reviewed
            await uow.commit()


def get_list_disliked_answers_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> ListDislikedAnswersUseCase:
    return ListDislikedAnswersUseCase(uow=uow)


def get_review_disliked_answer_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> ReviewDislikedAnswerUseCase:
    return ReviewDislikedAnswerUseCase(uow=uow)


class QuestionAnalyticsUseCase:
    """Savollar tahlili: eng ko'p so'ralganlar va bazada javob topilmaganlar."""

    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, days: int = 30, limit: int = 20) -> QuestionAnalyticsView:
        async with self.uow as uow:
            repo = uow.question_logs
            total, no_info, errors, avg_ms, tokens = await repo.summary(
                uow.session, days=days
            )
            top = await repo.top_questions(uow.session, days=days, limit=limit)
            unanswered = await repo.top_questions(
                uow.session, days=days, limit=limit, outcome="no_info"
            )

        def items(rows: list[tuple]) -> list[QuestionStatItem]:
            return [
                QuestionStatItem(question=q, count=c, users=u, last_asked=last)
                for q, c, u, last in rows
            ]

        return QuestionAnalyticsView(
            days=days,
            summary=QuestionSummary(
                total=total,
                no_info=no_info,
                errors=errors,
                avg_duration_ms=round(avg_ms),
                total_tokens=tokens,
            ),
            top=items(top),
            unanswered=items(unanswered),
        )


def get_question_analytics_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> QuestionAnalyticsUseCase:
    return QuestionAnalyticsUseCase(uow=uow)


class SystemStatusUseCase:
    """Tizim holati: komponentlar + so'nggi 24 soatdagi bot ishlashi."""

    HOURS = 24

    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
        readiness: ReadinessService,
    ) -> None:
        self.uow = uow
        self.readiness = readiness

    async def execute(self) -> SystemStatusView:
        components = await self.readiness.check_all()
        async with self.uow as uow:
            repo = uow.question_logs
            hourly = await repo.hourly(uow.session, hours=self.HOURS)
            p50, p95, mx = await repo.latency_percentiles(uow.session, hours=self.HOURS)
            total, no_info, errors, _avg, tokens = await repo.summary(uow.session, days=1)
        try:
            cache_hits, cache_misses = await cache_stats_today(self.readiness.redis)
        except Exception:  # noqa: BLE001 - Redis yiqilgan bo'lsa komponent kartasi ko'rsatadi
            cache_hits = cache_misses = 0

        # Bo'sh soatlar ham grafikda 0 bo'lib turishi uchun 24 ta nuqtani to'ldiramiz
        by_hour = {h.replace(minute=0, second=0, microsecond=0): row for h, *row in hourly}
        now = get_utc_now().replace(minute=0, second=0, microsecond=0)
        points: list[HourlyPoint] = []
        for i in range(self.HOURS - 1, -1, -1):
            h = now - timedelta(hours=i)
            q, e, n, avg = by_hour.get(h, (0, 0, 0, 0.0))
            points.append(HourlyPoint(hour=h, questions=q, errors=e, no_info=n, avg_ms=round(avg)))

        return SystemStatusView(
            status=overall_status(components),
            checked_at=get_utc_now(),
            components=[
                ComponentStatusView(
                    name=c.name,
                    ok=c.ok,
                    latency_ms=c.latency_ms,
                    critical=c.critical,
                    detail=c.detail,
                )
                for c in components
            ],
            llm=LlmMetrics(
                hours=self.HOURS,
                questions=total,
                errors=errors,
                no_info=no_info,
                tokens=tokens,
                p50_ms=p50,
                p95_ms=p95,
                max_ms=mx,
                hourly=points,
                cache_hits_today=cache_hits,
                cache_misses_today=cache_misses,
            ),
        )


def get_system_status_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
    readiness: ReadinessService = Depends(get_readiness_service),
) -> SystemStatusUseCase:
    return SystemStatusUseCase(uow=uow, readiness=readiness)


class ListFlaggedQuestionsUseCase:
    """Xavfli so'rovlar va so'kinishlar ro'yxati (savol matni maskalangan)."""

    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, page: int = 1, size: int = 50) -> FlaggedQuestionPageView:
        async with self.uow as uow:
            rows, total = await uow.question_logs.list_flagged(uow.session, page=page, size=size)
        return FlaggedQuestionPageView(
            items=[
                FlaggedQuestionView(
                    id=log.id,
                    created_at=log.created_at,
                    kind=log.intent or "harmful",
                    question=log.question,
                    username=username,
                    user_name=name,
                )
                for log, username, name in rows
            ],
            total=total,
        )


def get_list_flagged_questions_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> ListFlaggedQuestionsUseCase:
    return ListFlaggedQuestionsUseCase(uow=uow)

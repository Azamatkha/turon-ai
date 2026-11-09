"""
Admin statistika endpointi.

SWAGGER'DA TEKSHIRISH:
1) admin bilan login qiling, "Authorize" ga tokenni kiriting.
2) GET /v1/admin/stats -> jami userlar/suhbatlar/xabarlar + bo'limlar ulushi.
9) GET /v1/admin/flagged-questions -> xavfli so'rovlar va so'kinishlar
   (yashirin so'rovlar ham — router modeli ma'nosidan aniqlaydi).
8) GET /v1/admin/system -> komponentlar holati (Postgres, Redis, Qdrant,
   Ollama, RabbitMQ, Celery) + so'nggi 24 soatda bot ishlashi (p50/p95).
7) GET /v1/admin/backups -> zaxira nusxalar holati va fayllar;
   POST /v1/admin/backups/qdrant -> bilim bazasi snapshot'ini hoziroq olish.
6) GET /v1/admin/audit-logs?target_type=user&search=... -> admin amallari
   jurnali (kim, nima qildi, nimaga, qachon). Faqat VIEW_LOGS huquqi bilan.
5) GET /v1/admin/questions?days=30 -> eng ko'p so'ralgan va bazada javob
   topilmagan savollar + umumiy ko'rsatkichlar (javob vaqti, token).
4) GET /v1/admin/disliked-answers?only_open=true -> dislike olgan javoblar
   (savol, javob, manba, sabab); PATCH .../{id} {"reviewed": true}.
3) GET /v1/admin/face-id-logs?only_failed=true -> /auth/save ga kelgan GSI
   signature'lar (xato bilan tugaganlari ham), vaqti va natijasi bilan.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.admin.schemas import (
    DashboardStatsView,
    DislikedAnswerPageView,
    FaceIdLogPageView,
    FlaggedQuestionPageView,
    QuestionAnalyticsView,
    ReviewDislikedModel,
    SystemStatusView,
)
from src.admin.usecases import (
    DashboardStatsUseCase,
    ListDislikedAnswersUseCase,
    ListFaceIdLogsUseCase,
    ListFlaggedQuestionsUseCase,
    QuestionAnalyticsUseCase,
    ReviewDislikedAnswerUseCase,
    SystemStatusUseCase,
    get_dashboard_stats_use_case,
    get_list_disliked_answers_use_case,
    get_list_face_id_logs_use_case,
    get_list_flagged_questions_use_case,
    get_question_analytics_use_case,
    get_review_disliked_answer_use_case,
    get_system_status_use_case,
)
from src.audit.actions import AuditAction
from src.audit.schemas import AuditLogPageView
from src.audit.usecases import (
    AuditRecorder,
    ListAuditLogsUseCase,
    get_audit_recorder,
    get_list_audit_logs_use_case,
)
from src.backup.schemas import BackupOverviewView
from src.backup.usecases import BackupOverviewUseCase, TriggerQdrantBackupUseCase
from src.user.auth.permissions.checker import require_permission
from src.user.auth.permissions.enum import Permission
from src.user.models import User

router = APIRouter()


@router.get("/stats", response_model=DashboardStatsView)
async def dashboard_stats(
    current_user: Annotated[User, Depends(require_permission(Permission.VIEW_DASHBOARD))],
    use_case: Annotated[DashboardStatsUseCase, Depends(get_dashboard_stats_use_case)],
) -> DashboardStatsView:
    """Dashboard uchun real statistika."""
    return await use_case.execute()


@router.get("/face-id-logs", response_model=FaceIdLogPageView)
async def list_face_id_logs(
    current_user: Annotated[User, Depends(require_permission(Permission.VIEW_LOGS))],
    use_case: Annotated[
        ListFaceIdLogsUseCase, Depends(get_list_face_id_logs_use_case)
    ],
    only_failed: bool = False,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> FaceIdLogPageView:
    """`/auth/save` ga kelgan GSI signature'lar — nima kelgani va natijasi.

    Shaxsiy ma'lumot qaytadi, shuning uchun faqat VIEW_LOGS huquqi bilan.
    """
    return await use_case.execute(only_failed=only_failed, page=page, size=size)


@router.get("/disliked-answers", response_model=DislikedAnswerPageView)
async def list_disliked_answers(
    current_user: Annotated[User, Depends(require_permission(Permission.VIEW_REPORTS))],
    use_case: Annotated[
        ListDislikedAnswersUseCase, Depends(get_list_disliked_answers_use_case)
    ],
    only_open: bool = True,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DislikedAnswerPageView:
    """Yoqmagan javoblar navbati — bilim bazasini tuzatish uchun."""
    return await use_case.execute(only_open=only_open, page=page, size=size)


@router.patch(
    "/disliked-answers/{message_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def review_disliked_answer(
    message_id: UUID,
    data: ReviewDislikedModel,
    current_user: Annotated[User, Depends(require_permission(Permission.MANAGE_REPORTS))],
    use_case: Annotated[
        ReviewDislikedAnswerUseCase, Depends(get_review_disliked_answer_use_case)
    ],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
) -> None:
    """Javobni "ko'rib chiqildi" deb belgilash (yoki qayta ochish)."""
    await use_case.execute(message_id=message_id, reviewed=data.reviewed)
    await audit.log(
        current_user, AuditAction.ANSWER_REVIEW, "message", message_id,
        details={"reviewed": data.reviewed},
    )


@router.get("/questions", response_model=QuestionAnalyticsView)
async def question_analytics(
    current_user: Annotated[User, Depends(require_permission(Permission.VIEW_DASHBOARD))],
    use_case: Annotated[
        QuestionAnalyticsUseCase, Depends(get_question_analytics_use_case)
    ],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> QuestionAnalyticsView:
    """Savollar tahlili — bilim bazasiga nima qo'shish kerakligini ko'rsatadi."""
    return await use_case.execute(days=days, limit=limit)


@router.get("/audit-logs", response_model=AuditLogPageView)
async def list_audit_logs(
    current_user: Annotated[User, Depends(require_permission(Permission.VIEW_LOGS))],
    use_case: Annotated[ListAuditLogsUseCase, Depends(get_list_audit_logs_use_case)],
    target_type: str | None = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> AuditLogPageView:
    """Admin amallari jurnali — yangisidan eskisiga."""
    return await use_case.execute(
        target_type=target_type, search=search, page=page, size=size
    )


@router.get("/backups", response_model=BackupOverviewView)
async def backup_overview(
    current_user: Annotated[User, Depends(require_permission(Permission.MANAGE_BACKUPS))],
) -> BackupOverviewView:
    """Zaxira nusxalar: har tur bo'yicha oxirgi natija va fayllar ro'yxati."""
    return BackupOverviewUseCase().execute()


@router.post("/backups/qdrant", status_code=status.HTTP_202_ACCEPTED)
async def run_qdrant_backup(
    current_user: Annotated[User, Depends(require_permission(Permission.MANAGE_BACKUPS))],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
) -> None:
    """Bilim bazasi (Qdrant) snapshot'ini hoziroq navbatga qo'yadi."""
    TriggerQdrantBackupUseCase().execute()
    await audit.log(current_user, AuditAction.BACKUP_RUN, "backup", target_label="qdrant")


@router.get("/system", response_model=SystemStatusView)
async def system_status(
    current_user: Annotated[User, Depends(require_permission(Permission.VIEW_LOGS))],
    use_case: Annotated[SystemStatusUseCase, Depends(get_system_status_use_case)],
) -> SystemStatusView:
    """Tizim holati: komponentlar va bot ishlash ko'rsatkichlari."""
    return await use_case.execute()


@router.get("/flagged-questions", response_model=FlaggedQuestionPageView)
async def list_flagged_questions(
    current_user: Annotated[User, Depends(require_permission(Permission.VIEW_LOGS))],
    use_case: Annotated[
        ListFlaggedQuestionsUseCase, Depends(get_list_flagged_questions_use_case)
    ],
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> FlaggedQuestionPageView:
    """Xavfli so'rovlar va so'kinishlar — kim, qachon, nima yozgan."""
    return await use_case.execute(page=page, size=size)

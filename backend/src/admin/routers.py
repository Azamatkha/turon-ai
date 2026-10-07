"""
Admin statistika endpointi.

SWAGGER'DA TEKSHIRISH:
1) admin bilan login qiling, "Authorize" ga tokenni kiriting.
2) GET /v1/admin/stats -> jami userlar/suhbatlar/xabarlar + bo'limlar ulushi.
3) GET /v1/admin/face-id-logs?only_failed=true -> /auth/save ga kelgan GSI
   signature'lar (xato bilan tugaganlari ham), vaqti va natijasi bilan.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.admin.schemas import DashboardStatsView, FaceIdLogPageView
from src.admin.usecases import (
    DashboardStatsUseCase,
    ListFaceIdLogsUseCase,
    get_dashboard_stats_use_case,
    get_list_face_id_logs_use_case,
)
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

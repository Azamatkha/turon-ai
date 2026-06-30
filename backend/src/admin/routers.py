"""
Admin statistika endpointi.

SWAGGER'DA TEKSHIRISH:
1) admin bilan login qiling, "Authorize" ga tokenni kiriting.
2) GET /v1/admin/stats -> jami userlar/suhbatlar/xabarlar + bo'limlar ulushi.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from src.admin.schemas import DashboardStatsView
from src.admin.usecases import (
    DashboardStatsUseCase,
    get_dashboard_stats_use_case,
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

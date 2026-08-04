"""Foydalanuvchi murojaatlari (muammo / taklif) endpointlari.

Ikkita router bor:
  • `router`       — /v1/reports        : har qanday kirgan foydalanuvchi yuboradi
  • `admin_router` — /v1/admin/reports  : admin ko'radi va holatini o'zgartiradi

Skrinshot statik papkadan berilmaydi — faqat VIEW_REPORTS huquqi bor odam
`/v1/admin/reports/{id}/screenshot` orqali ocha oladi.

─── SWAGGER'DA QANDAY TEKSHIRISH ───────────────────────────────────────────
1) Oddiy foydalanuvchi bilan kiring va "Authorize" qiling.
2) POST /v1/reports  (multipart): kind=problem, title=..., description=...,
   screenshot=<png fayl>                                   -> 201
3) Admin bilan kiring:
   GET   /v1/admin/reports?status=new                      -> ro'yxat
   GET   /v1/admin/reports/{id}/screenshot                 -> rasm
   PATCH /v1/admin/reports/{id}  {"status":"resolved"}     -> holat o'zgaradi
─────────────────────────────────────────────────────────────────────────────
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse

from src.core.errors.exceptions import NotAcceptableException
from src.core.storage.media import resolve_media_path
from src.reports.enums import ReportKind
from src.reports.schemas import (
    ReportAdminView,
    ReportPageView,
    ReportView,
    UpdateReportModel,
)
from src.reports.usecases import (
    CreateReportUseCase,
    GetReportScreenshotUseCase,
    GetReportUseCase,
    ListReportsUseCase,
    UpdateReportUseCase,
    get_create_report_use_case,
    get_get_report_use_case,
    get_list_reports_use_case,
    get_report_screenshot_use_case,
    get_update_report_use_case,
)
from src.user.auth.dependencies import get_current_user
from src.user.auth.permissions.checker import require_permission
from src.user.auth.permissions.enum import Permission
from src.user.models import User

router = APIRouter()
admin_router = APIRouter()

BAD_KIND = "kind faqat 'problem' yoki 'suggestion' bo'lishi mumkin"


@router.post("", status_code=201, response_model=ReportView)
async def create_report(
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[CreateReportUseCase, Depends(get_create_report_use_case)],
    kind: Annotated[str, Form()],
    title: Annotated[str, Form(min_length=1, max_length=200)],
    description: Annotated[str, Form(min_length=1, max_length=5000)],
    screenshot: Annotated[UploadFile | None, File()] = None,
) -> ReportView:
    """Muammo haqida xabar yoki taklif yuboradi (skrinshot ixtiyoriy)."""
    if kind not in ReportKind.values():
        raise NotAcceptableException(BAD_KIND)
    return await use_case.execute(
        user_id=current_user.id,
        kind=kind,
        title=title,
        description=description,
        screenshot=screenshot,
    )


@admin_router.get("", response_model=ReportPageView)
async def list_reports(
    current_user: Annotated[
        User, Depends(require_permission(Permission.VIEW_REPORTS))
    ],
    use_case: Annotated[ListReportsUseCase, Depends(get_list_reports_use_case)],
    status: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ReportPageView:
    """Admin: murojaatlar ro'yxati (holat bo'yicha filtrlash mumkin)."""
    return await use_case.execute(status=status, page=page, size=size)


@admin_router.get("/{report_id}", response_model=ReportAdminView)
async def get_report(
    report_id: UUID,
    current_user: Annotated[
        User, Depends(require_permission(Permission.VIEW_REPORTS))
    ],
    use_case: Annotated[GetReportUseCase, Depends(get_get_report_use_case)],
) -> ReportAdminView:
    """Admin: bitta murojaat tafsiloti."""
    return await use_case.execute(report_id=report_id)


@admin_router.get("/{report_id}/screenshot")
async def get_report_screenshot(
    report_id: UUID,
    current_user: Annotated[
        User, Depends(require_permission(Permission.VIEW_REPORTS))
    ],
    use_case: Annotated[
        GetReportScreenshotUseCase, Depends(get_report_screenshot_use_case)
    ],
) -> FileResponse:
    """Admin: murojaatga biriktirilgan skrinshot.

    Fayl ochiq URL'da turmaydi — bu yerda huquq tekshiriladi va shundan keyin
    diskdan o'qiladi.
    """
    relative_path = await use_case.execute(report_id=report_id)
    return FileResponse(resolve_media_path(relative_path))


@admin_router.patch("/{report_id}", response_model=ReportAdminView)
async def update_report(
    report_id: UUID,
    data: UpdateReportModel,
    current_user: Annotated[
        User, Depends(require_permission(Permission.MANAGE_REPORTS))
    ],
    use_case: Annotated[UpdateReportUseCase, Depends(get_update_report_use_case)],
) -> ReportAdminView:
    """Admin: murojaat holatini va izohini yangilaydi."""
    return await use_case.execute(report_id=report_id, data=data)

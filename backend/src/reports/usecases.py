from uuid import UUID

from fastapi import Depends, UploadFile

from loggers import get_logger
from src.core.database.session import get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.errors.exceptions import InstanceNotFoundException
from src.core.storage.media import save_image
from src.core.utils.datetime_utils import get_utc_now
from src.main.config import config
from src.notifications.enums import NotificationType
from src.notifications.events import publish_new
from src.reports.enums import ReportStatus
from src.reports.models import UserReport
from src.reports.schemas import (
    ReportAdminView,
    ReportPageView,
    ReportView,
    UpdateReportModel,
)
from src.user.enums import UserRole
from src.user.models import User

logger = get_logger(__name__)

REPORT_NOT_FOUND = "Murojaat topilmadi"
SCREENSHOT_NOT_FOUND = "Skrinshot topilmadi"
SCREENSHOT_SUBDIR = "reports"


def _to_view(report: UserReport) -> ReportView:
    return ReportView(
        id=report.id,
        kind=report.kind,
        title=report.title,
        description=report.description,
        status=report.status,
        has_screenshot=bool(report.screenshot_path),
        created_at=report.created_at,
    )


def _to_admin_view(report: UserReport, author: User) -> ReportAdminView:
    return ReportAdminView(
        id=report.id,
        kind=report.kind,
        title=report.title,
        description=report.description,
        status=report.status,
        has_screenshot=bool(report.screenshot_path),
        created_at=report.created_at,
        user_name=author.full_name,
        user_department=author.department,
        admin_comment=report.admin_comment,
        resolved_at=report.resolved_at,
    )


class CreateReportUseCase:
    """Murojaatni saqlaydi va adminlarga bildirishnoma yozadi.

    Skrinshot avval diskka yoziladi (tekshiruvlardan o'tgach), so'ng bitta
    tranzaksiyada murojaat va bildirishnomalar yoziladi.
    """

    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self,
        user_id: UUID,
        kind: str,
        title: str,
        description: str,
        screenshot: UploadFile | None = None,
    ) -> ReportView:
        screenshot_path: str | None = None
        if screenshot is not None and screenshot.filename:
            screenshot_path, _ = await save_image(
                screenshot,
                subdir=SCREENSHOT_SUBDIR,
                max_bytes=config.app.REPORT_MAX_BYTES,
            )

        async with self.uow as uow:
            report = await uow.reports.create(
                uow.session,
                {
                    "user_id": user_id,
                    "kind": kind,
                    "title": title,
                    "description": description,
                    "screenshot_path": screenshot_path,
                    "status": ReportStatus.NEW.value,
                },
            )
            # id kerak — bildirishnoma unga havola qiladi
            await uow.session.flush()
            admins = await uow.notifications.fan_out(
                uow.session,
                notification_type=NotificationType.REPORT_NEW,
                params={"title": title},
                entity_id=report.id,
                role=UserRole.ADMIN,
            )
            await uow.commit()
            view = _to_view(report)

        # Signal commit'dan keyin — adminlarning ochiq oqimlari darhol xabar oladi
        await publish_new(admins)
        return view


class ListReportsUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self, status: str | None = None, page: int = 1, size: int = 20
    ) -> ReportPageView:
        async with self.uow as uow:
            rows, total = await uow.reports.list_with_users(
                uow.session, status=status, page=page, size=size
            )
            new_count = await uow.reports.count(
                uow.session, status=ReportStatus.NEW.value
            )
            return ReportPageView(
                items=[_to_admin_view(report, author) for report, author in rows],
                total=total,
                new_count=new_count,
            )


class GetReportUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, report_id: UUID) -> ReportAdminView:
        async with self.uow as uow:
            row = await uow.reports.get_with_user(uow.session, report_id)
            if not row:
                raise InstanceNotFoundException(REPORT_NOT_FOUND)
            return _to_admin_view(row[0], row[1])


class GetReportScreenshotUseCase:
    """Skrinshot faylining diskdagi nisbiy yo'lini qaytaradi."""

    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(self, report_id: UUID) -> str:
        async with self.uow as uow:
            report = await uow.reports.get_single(uow.session, id=report_id)
            if not report:
                raise InstanceNotFoundException(REPORT_NOT_FOUND)
            if not report.screenshot_path:
                raise InstanceNotFoundException(SCREENSHOT_NOT_FOUND)
            return report.screenshot_path


class UpdateReportUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self, report_id: UUID, data: UpdateReportModel
    ) -> ReportAdminView:
        async with self.uow as uow:
            row = await uow.reports.get_with_user(uow.session, report_id)
            if not row:
                raise InstanceNotFoundException(REPORT_NOT_FOUND)
            report, author = row
            report.status = data.status
            report.admin_comment = data.admin_comment
            report.resolved_at = (
                get_utc_now() if data.status == ReportStatus.RESOLVED else None
            )
            await uow.commit()
            return _to_admin_view(report, author)


# ---- DI factory'lar ----
def get_create_report_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> CreateReportUseCase:
    return CreateReportUseCase(uow=uow)


def get_list_reports_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> ListReportsUseCase:
    return ListReportsUseCase(uow=uow)


def get_get_report_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> GetReportUseCase:
    return GetReportUseCase(uow=uow)


def get_report_screenshot_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> GetReportScreenshotUseCase:
    return GetReportScreenshotUseCase(uow=uow)


def get_update_report_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> UpdateReportUseCase:
    return UpdateReportUseCase(uow=uow)

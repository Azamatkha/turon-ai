from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from src.core.schemas import Base
from src.reports.enums import ReportStatus


class ReportView(Base):
    """Murojaatning foydalanuvchiga ko'rinadigan qismi."""

    id: UUID
    kind: str
    title: str
    description: str
    status: str
    # Skrinshot bor-yo'qligi. Faylning o'zi alohida (huquq tekshiriladigan)
    # endpoint orqali olinadi — bu yerda yo'l qaytarilmaydi.
    has_screenshot: bool = False
    created_at: datetime


class ReportAdminView(ReportView):
    """Admin panel uchun qo'shimcha maydonlar."""

    user_name: str = ""
    user_department: str | None = None
    admin_comment: str = ""
    resolved_at: datetime | None = None


class ReportPageView(Base):
    items: list[ReportAdminView]
    total: int
    new_count: int


class UpdateReportModel(Base):
    status: str
    admin_comment: str = Field("", max_length=5000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in ReportStatus.values():
            raise ValueError(
                "status faqat new, in_progress yoki resolved bo'lishi mumkin"
            )
        return value

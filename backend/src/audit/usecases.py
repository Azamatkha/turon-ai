from typing import Any
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import select

from loggers import get_logger
from src.audit.actions import SECRET_FIELDS, AuditAction
from src.audit.schemas import AuditLogPageView, AuditLogView
from src.core.database.session import async_session, get_unit_of_work
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol, get_uow
from src.user.models import User

logger = get_logger(__name__)


def _clean(value: Any) -> Any:
    """details JSONB'ga yoziladigan qiymat: sirlar olib tashlanadi, sana/UUID
    kabi tiplar matnga aylanadi."""
    if isinstance(value, dict):
        return {
            str(k): ("***" if str(k) in SECRET_FIELDS else _clean(v))
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [_clean(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


class AuditRecorder:
    """Admin amalini audit jurnaliga yozadi.

    Router amal MUVAFFAQIYATLI tugagach chaqiradi — xato bilan tugagan amal
    yozilmaydi. O'z sessiyasida ishlaydi: usecase tranzaksiyasiga bog'liq
    emas va yozib bo'lmasa amalning o'zini buzmaydi (faqat log).
    """

    def __init__(self, request: Request) -> None:
        self.ip = request.client.host if request.client else None

    async def log(
        self,
        actor: User,
        action: AuditAction,
        target_type: str,
        target_id: UUID | str | None = None,
        target_label: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        try:
            async with async_session() as session:
                uow = await get_uow(session)
                async with uow:
                    # Obyekt nomi berilmagan user uchun — bazadan loginini olamiz
                    # (o'chirilgan user ham yumshoq o'chiriladi, satr qoladi)
                    # get_single emas: u o'chirilganlarni yashiradi, bizga esa
                    # endigina o'chirilgan userning ham logini kerak.
                    if target_label is None and target_type == "user" and target_id:
                        target_label = (
                            await uow.session.execute(
                                select(User.username).where(User.id == target_id)
                            )
                        ).scalar_one_or_none()
                    await uow.audit_logs.create(
                        uow.session,
                        {
                            "actor_id": actor.id,
                            "actor_username": actor.username,
                            "action": str(action),
                            "target_type": target_type,
                            "target_id": str(target_id) if target_id else None,
                            "target_label": (target_label or "")[:300] or None,
                            "details": _clean(details) if details else None,
                            "ip": self.ip,
                        },
                    )
                    await uow.commit()
        except Exception:  # noqa: BLE001 - audit amalni buzmasin
            logger.exception("Audit yozuvini saqlab bo'lmadi: %s", action)


def get_audit_recorder(request: Request) -> AuditRecorder:
    return AuditRecorder(request)


class ListAuditLogsUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]) -> None:
        self.uow = uow

    async def execute(
        self,
        target_type: str | None = None,
        search: str | None = None,
        page: int = 1,
        size: int = 50,
    ) -> AuditLogPageView:
        async with self.uow as uow:
            rows, total = await uow.audit_logs.list_page(
                uow.session,
                target_type=target_type,
                search=search,
                page=page,
                size=size,
            )
            return AuditLogPageView(
                items=[AuditLogView.model_validate(r) for r in rows], total=total
            )


def get_list_audit_logs_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> ListAuditLogsUseCase:
    return ListAuditLogsUseCase(uow=uow)

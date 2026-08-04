"""Kunlik vazifa: eskirgan bildirishnomalarni tozalaydi.

Har bir tizim xabari har bir aktiv foydalanuvchiga bittadan qator yozadi,
shuning uchun jadval tozalanmasa vaqt o'tib kattalashib ketadi.
"""

from datetime import timedelta

from celery_tasks.main import (
    celery_app,  # noqa: F401
    local_async_session,
)
from celery_tasks.types import typed_shared_task
from loggers import get_logger
from src.core.database.uow import ApplicationUnitOfWork, RepositoryProtocol
from src.core.utils.coroutine_runner import execute_coroutine_sync
from src.core.utils.datetime_utils import get_utc_now

logger = get_logger(__name__)

# O'qilganlari 30 kundan keyin, o'qilmaganlari 90 kundan keyin o'chadi
READ_RETENTION_DAYS = 30
MAX_RETENTION_DAYS = 90


@typed_shared_task(name="cleanup_old_notifications")
def cleanup_old_notifications() -> str:
    deleted = execute_coroutine_sync(coroutine=_cleanup_old_notifications)
    return f"Deleted {deleted} notifications."


async def _cleanup_old_notifications() -> int:
    now = get_utc_now()
    async with local_async_session() as session:
        uow: ApplicationUnitOfWork[RepositoryProtocol] = ApplicationUnitOfWork(session)
        try:
            async with uow:
                deleted = await uow.notifications.delete_older_than(
                    uow.session,
                    read_before=now - timedelta(days=READ_RETENTION_DAYS),
                    any_before=now - timedelta(days=MAX_RETENTION_DAYS),
                )
                await uow.commit()
                return deleted
        except Exception:
            logger.exception("Eski bildirishnomalarni tozalab bo'lmadi")
            return 0

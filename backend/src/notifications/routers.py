"""Bildirishnoma (notification) endpointlari.

Hammasi joriy foydalanuvchiga tegishli — birovning bildirishnomasini ko'rib
yoki o'qilgan deb belgilab bo'lmaydi (so'rovlar user_id bilan filtrlanadi).

─── SWAGGER'DA QANDAY TEKSHIRISH ───────────────────────────────────────────
1) /v1/users/auth/login orqali kirib, access_token oling va "Authorize" qiling.
2) Admin sifatida hujjat yuklang (POST /v1/admin/knowledge/pdf) —
   barcha aktiv foydalanuvchilarga bildirishnoma tarqaladi.
3) GET  /v1/notifications/unread-count   -> {"count": 1}
4) GET  /v1/notifications                -> ro'yxat + unread_count + total
5) POST /v1/notifications/{id}/read      -> {"success": true}
6) POST /v1/notifications/read-all       -> {"success": true}, count 0 ga tushadi
─────────────────────────────────────────────────────────────────────────────
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.core.schemas import SuccessResponse
from src.notifications.schemas import NotificationListView, UnreadCountView
from src.notifications.usecases import (
    ListNotificationsUseCase,
    MarkAllReadUseCase,
    MarkReadUseCase,
    UnreadCountUseCase,
    get_list_notifications_use_case,
    get_mark_all_read_use_case,
    get_mark_read_use_case,
    get_unread_count_use_case,
)
from src.user.auth.dependencies import get_current_user
from src.user.models import User

router = APIRouter()


@router.get("", response_model=NotificationListView)
async def list_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[
        ListNotificationsUseCase, Depends(get_list_notifications_use_case)
    ],
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
    only_unread: bool = False,
) -> NotificationListView:
    """Joriy foydalanuvchining bildirishnomalari (yangisidan eskisiga)."""
    return await use_case.execute(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        only_unread=only_unread,
    )


@router.get("/unread-count", response_model=UnreadCountView)
async def unread_count(
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[UnreadCountUseCase, Depends(get_unread_count_use_case)],
) -> UnreadCountView:
    """O'qilmagan bildirishnomalar soni — frontend buni interval bilan so'raydi."""
    return await use_case.execute(user_id=current_user.id)


@router.post("/read-all", response_model=SuccessResponse)
async def mark_all_read(
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[MarkAllReadUseCase, Depends(get_mark_all_read_use_case)],
) -> SuccessResponse:
    """Barcha bildirishnomalarni o'qilgan deb belgilaydi."""
    return await use_case.execute(user_id=current_user.id)


@router.post("/{notification_id}/read", response_model=SuccessResponse)
async def mark_read(
    notification_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[MarkReadUseCase, Depends(get_mark_read_use_case)],
) -> SuccessResponse:
    """Bitta bildirishnomani o'qilgan deb belgilaydi."""
    return await use_case.execute(
        user_id=current_user.id, notification_id=notification_id
    )

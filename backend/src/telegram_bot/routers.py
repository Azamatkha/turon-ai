"""Telegram yordam boti (aihelp) ma'lumotlari.

Ikkita router bor:
  • `router`       — /v1/telegram-bot        : bot o'zi push qiladi (X-Bot-Key bilan)
  • `admin_router` — /v1/admin/telegram-bot  : admin panelda ko'rish (faqat o'qish)

Bot bank noutbukida ishlaydi va serverga faqat public tunnel orqali chiqa oladi —
shuning uchun server botdan so'ramaydi, bot o'zi davriy yuboradi.

─── SWAGGER'DA QANDAY TEKSHIRISH ───────────────────────────────────────────
1) POST /v1/telegram-bot/sync, header X-Bot-Key: <TELEGRAM_BOT_API_KEY>
   {"users":[{"telegram_id":1,"full_name":"Test","first_seen_at":"2026-11-10T09:00:00Z"}],
    "messages":[{"bot_message_id":1,"telegram_id":1,"direction":"in","status":"new",
                 "text":"salom","sent_at":"2026-11-10T09:01:00Z"}]}       -> 200
2) Admin bilan kiring:
   GET /v1/admin/telegram-bot/users?search=test                    -> ro'yxat
   GET /v1/admin/telegram-bot/users/{id}/messages                  -> yozishmalar
─────────────────────────────────────────────────────────────────────────────
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.telegram_bot.dependencies import verify_bot_key
from src.telegram_bot.schemas import (
    BotSyncRequest,
    BotSyncResult,
    TgMessagePage,
    TgUserPage,
)
from src.telegram_bot.usecases import (
    ListTgMessagesUseCase,
    ListTgUsersUseCase,
    SyncBotDataUseCase,
    get_list_tg_messages_use_case,
    get_list_tg_users_use_case,
    get_sync_bot_data_use_case,
)
from src.user.auth.permissions.checker import require_permission
from src.user.auth.permissions.enum import Permission
from src.user.models import User

router = APIRouter()
admin_router = APIRouter()


@router.post(
    "/sync", response_model=BotSyncResult, dependencies=[Depends(verify_bot_key)]
)
async def sync_bot_data(
    data: BotSyncRequest,
    use_case: Annotated[SyncBotDataUseCase, Depends(get_sync_bot_data_use_case)],
) -> BotSyncResult:
    """Bot: userlar va xabarlarni yuboradi (qo'shiladi yoki yangilanadi)."""
    return await use_case.execute(data)


@admin_router.get("/users", response_model=TgUserPage)
async def list_tg_users(
    current_user: Annotated[
        User, Depends(require_permission(Permission.VIEW_TELEGRAM_BOT))
    ],
    use_case: Annotated[ListTgUsersUseCase, Depends(get_list_tg_users_use_case)],
    search: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> TgUserPage:
    """Admin: bot userlari (ism, username yoki telefon bo'yicha qidiruv)."""
    return await use_case.execute(search=search, page=page, size=size)


@admin_router.get("/users/{user_id}/messages", response_model=TgMessagePage)
async def list_tg_messages(
    user_id: UUID,
    current_user: Annotated[
        User, Depends(require_permission(Permission.VIEW_TELEGRAM_BOT))
    ],
    use_case: Annotated[ListTgMessagesUseCase, Depends(get_list_tg_messages_use_case)],
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> TgMessagePage:
    """Admin: bitta userning yozishmalari (yangisidan eskisiga)."""
    return await use_case.execute(user_id=user_id, page=page, size=size)

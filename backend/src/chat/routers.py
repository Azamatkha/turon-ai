"""
Chat (suhbat) endpointlari. Hammasi joriy foydalanuvchiga tegishli — boshqaning
suhbatini ko'rib/o'zgartirib bo'lmaydi (get_single user_id bilan filtrlanadi).

─── SWAGGER'DA QANDAY TEKSHIRISH ───────────────────────────────────────────
1) /v1/users/auth/login orqali kirib, access_token oling.
2) Swagger tepasidagi "Authorize" tugmasiga tokenni kiriting (Bearer).
3) POST /v1/chat/sessions   body: {"title": "Birinchi suhbat"}      -> 201, sessiya id
4) GET  /v1/chat/sessions                                          -> ro'yxat (1 ta)
5) POST /v1/chat/sessions/{id}/messages  {"role":"user","content":"Salom"}  -> 201
6) POST /v1/chat/sessions/{id}/messages  {"role":"assistant","content":"Salom!"}
7) GET  /v1/chat/sessions/{id}            -> sessiya + ikkala xabar (vaqt tartibida)
8) PATCH /v1/chat/sessions/{id}  {"title":"Yangi nom"}             -> nom o'zgaradi
9) DELETE /v1/chat/sessions/{id}                                    -> {"success": true}
─────────────────────────────────────────────────────────────────────────────
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from src.core.schemas import SuccessResponse
from src.user.auth.dependencies import get_current_user
from src.user.models import User
from src.chat.schemas import (
    AddMessageModel,
    CreateSessionModel,
    MessageView,
    RenameSessionModel,
    SessionDetailView,
    SessionView,
)
from src.chat.usecases import (
    AddMessageUseCase,
    CreateSessionUseCase,
    DeleteSessionUseCase,
    GetSessionUseCase,
    ListSessionsUseCase,
    RenameSessionUseCase,
    get_add_message_use_case,
    get_create_session_use_case,
    get_delete_session_use_case,
    get_get_session_use_case,
    get_list_sessions_use_case,
    get_rename_session_use_case,
)

router = APIRouter()


@router.get("/sessions", response_model=list[SessionView])
async def list_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[ListSessionsUseCase, Depends(get_list_sessions_use_case)],
) -> list[SessionView]:
    """Joriy foydalanuvchining barcha suhbatlari."""
    return await use_case.execute(user_id=current_user.id)


@router.post("/sessions", status_code=201, response_model=SessionView)
async def create_session(
    current_user: Annotated[User, Depends(get_current_user)],
    data: CreateSessionModel,
    use_case: Annotated[CreateSessionUseCase, Depends(get_create_session_use_case)],
) -> SessionView:
    """Yangi suhbat yaratish."""
    return await use_case.execute(user_id=current_user.id, title=data.title)


@router.get("/sessions/{session_id}", response_model=SessionDetailView)
async def get_session_detail(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[GetSessionUseCase, Depends(get_get_session_use_case)],
) -> SessionDetailView:
    """Bitta suhbat va uning xabarlari."""
    return await use_case.execute(user_id=current_user.id, session_id=session_id)


@router.patch("/sessions/{session_id}", response_model=SessionView)
async def rename_session(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    data: RenameSessionModel,
    use_case: Annotated[RenameSessionUseCase, Depends(get_rename_session_use_case)],
) -> SessionView:
    """Suhbat nomini o'zgartirish."""
    return await use_case.execute(
        user_id=current_user.id, session_id=session_id, title=data.title
    )


@router.delete("/sessions/{session_id}", response_model=SuccessResponse)
async def delete_session(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[DeleteSessionUseCase, Depends(get_delete_session_use_case)],
) -> SuccessResponse:
    """Suhbatni o'chirish (yumshoq)."""
    return await use_case.execute(user_id=current_user.id, session_id=session_id)


@router.post(
    "/sessions/{session_id}/messages", status_code=201, response_model=MessageView
)
async def add_message(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    data: AddMessageModel,
    use_case: Annotated[AddMessageUseCase, Depends(get_add_message_use_case)],
) -> MessageView:
    """Suhbatga xabar qo'shish (role: 'user' yoki 'assistant')."""
    return await use_case.execute(
        user_id=current_user.id, session_id=session_id, data=data
    )

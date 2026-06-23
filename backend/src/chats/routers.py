"""Chat tarixi endpointlari (foydalanuvchiga bog'langan, login talab qiladi)."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.chats.schemas import (
    AddMessage,
    CreateSession,
    MessageView,
    RenameSession,
    SessionDetail,
    SessionView,
)
from src.chats.service import ChatService
from src.core.database.session import get_session
from src.core.schemas import SuccessResponse
from src.simple_auth.dependencies import get_current_user
from src.user.models import User

router = APIRouter()


def _service(session: Annotated[AsyncSession, Depends(get_session)]) -> ChatService:
    return ChatService(session)


@router.get("", response_model=list[SessionView])
async def list_sessions(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ChatService, Depends(_service)],
) -> list[SessionView]:
    sessions = await service.list_sessions(user.id)
    return [SessionView.model_validate(s) for s in sessions]


@router.post("", response_model=SessionView, status_code=201)
async def create_session(
    payload: CreateSession,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ChatService, Depends(_service)],
) -> SessionView:
    session = await service.create_session(user.id, payload.title)
    return SessionView.model_validate(session)


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session_detail(
    session_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ChatService, Depends(_service)],
) -> SessionDetail:
    session = await service.get_session(user.id, session_id)
    return SessionDetail.model_validate(session)


@router.patch("/{session_id}", response_model=SessionView)
async def rename_session(
    session_id: UUID,
    payload: RenameSession,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ChatService, Depends(_service)],
) -> SessionView:
    session = await service.rename_session(user.id, session_id, payload.title)
    return SessionView.model_validate(session)


@router.delete("/{session_id}", response_model=SuccessResponse)
async def delete_session(
    session_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ChatService, Depends(_service)],
) -> SuccessResponse:
    await service.delete_session(user.id, session_id)
    return SuccessResponse(success=True)


@router.post("/{session_id}/messages", response_model=MessageView, status_code=201)
async def add_message(
    session_id: UUID,
    payload: AddMessage,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ChatService, Depends(_service)],
) -> MessageView:
    message = await service.add_message(
        user.id, session_id, payload.role, payload.content
    )
    return MessageView.model_validate(message)

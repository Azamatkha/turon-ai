"""Admin endpointlari: foydalanuvchilarni ko'rish/qo'shish/o'chirish/rol almashtirish.

Barchasi faqat ADMIN uchun (get_current_admin).
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin_panel.schemas import (
    AdminUserCreate,
    AdminUserUpdate,
    AdminUserView,
    RoleUpdate,
    UsersListResponse,
)
from src.admin_panel.service import AdminUserService
from src.core.database.session import get_session
from src.core.schemas import SuccessResponse
from src.simple_auth.dependencies import get_current_admin
from src.user.models import User

router = APIRouter(dependencies=[Depends(get_current_admin)])


def _service(session: Annotated[AsyncSession, Depends(get_session)]) -> AdminUserService:
    return AdminUserService(session)


@router.get("/users", response_model=UsersListResponse)
async def list_users(
    service: Annotated[AdminUserService, Depends(_service)],
    search: str | None = Query(default=None),
    department: str | None = Query(default=None),
) -> UsersListResponse:
    users = await service.list_users(search=search, department=department)
    return UsersListResponse(
        total=len(users),
        users=[AdminUserView.model_validate(u) for u in users],
    )


@router.post("/users", response_model=AdminUserView, status_code=201)
async def create_user(
    payload: AdminUserCreate,
    service: Annotated[AdminUserService, Depends(_service)],
) -> AdminUserView:
    user: User = await service.create_user(
        username=payload.username,
        full_name=payload.full_name,
        password=payload.password,
        role=payload.role,
        department=payload.department,
    )
    return AdminUserView.model_validate(user)


@router.patch("/users/{user_id}/role", response_model=AdminUserView)
async def change_role(
    user_id: UUID,
    payload: RoleUpdate,
    service: Annotated[AdminUserService, Depends(_service)],
) -> AdminUserView:
    user = await service.change_role(user_id, payload.role)
    return AdminUserView.model_validate(user)


@router.patch("/users/{user_id}", response_model=AdminUserView)
async def update_user(
    user_id: UUID,
    payload: AdminUserUpdate,
    service: Annotated[AdminUserService, Depends(_service)],
) -> AdminUserView:
    user = await service.update_user(
        user_id,
        username=payload.username,
        full_name=payload.full_name,
        password=payload.password,
        department=payload.department,
    )
    return AdminUserView.model_validate(user)


@router.delete("/users/{user_id}", response_model=SuccessResponse)
async def delete_user(
    user_id: UUID,
    service: Annotated[AdminUserService, Depends(_service)],
) -> SuccessResponse:
    await service.delete_user(user_id)
    return SuccessResponse(success=True)

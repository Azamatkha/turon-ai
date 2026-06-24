"""
HTTP endpoints for the Turon AI assistant: auth, chat, and admin.

Mounted under /v1 (see src/main/presentation.py), giving:
    /v1/auth/register, /v1/auth/login, /v1/auth/me
    /v1/chat/ask, /v1/chat/sessions, /v1/chat/sessions/{id}/messages
    /v1/admin/accounts, /v1/admin/accounts/{id}/role
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import get_session
from src.turon import service
from src.turon.dependencies import get_current_account, require_admin
from src.turon.models import Account
from src.turon.schemas import (
    AccountOut,
    AskRequest,
    AskResponse,
    ChatSessionOut,
    LoginRequest,
    MessageOut,
    RegisterRequest,
    TokenResponse,
    UpdateRoleRequest,
)
from src.turon.security import create_access_token

auth_router = APIRouter(prefix="/auth", tags=["Turon Auth"])
chat_router = APIRouter(prefix="/chat", tags=["Turon Chat"])
admin_router = APIRouter(prefix="/admin", tags=["Turon Admin"])


# ----- Auth ----- #
@auth_router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    payload: RegisterRequest, session: AsyncSession = Depends(get_session)
) -> TokenResponse:
    """Create an account (role = xodim) and return a token immediately."""
    account = await service.register_account(
        session,
        full_name=payload.full_name,
        login=payload.login,
        password=payload.password,
        department=payload.department,
    )
    token = create_access_token(account.id, account.role)
    return TokenResponse(
        access_token=token, account=AccountOut.model_validate(account)
    )


@auth_router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, session: AsyncSession = Depends(get_session)
) -> TokenResponse:
    """Verify credentials and return a JWT + profile."""
    account = await service.authenticate_account(
        session, login=payload.login, password=payload.password
    )
    token = create_access_token(account.id, account.role)
    return TokenResponse(
        access_token=token, account=AccountOut.model_validate(account)
    )


@auth_router.get("/me", response_model=AccountOut)
async def me(
    account: Annotated[Account, Depends(get_current_account)],
) -> AccountOut:
    """Return the currently authenticated account's profile."""
    return AccountOut.model_validate(account)


# ----- Chat ----- #
@chat_router.post("/ask", response_model=AskResponse)
async def ask(
    payload: AskRequest,
    account: Annotated[Account, Depends(get_current_account)],
    session: AsyncSession = Depends(get_session),
) -> AskResponse:
    """Store the question, return the fixed answer, and save both to history."""
    chat_session, user_msg, assistant_msg = await service.ask(
        session, account, payload.question, payload.session_id
    )
    return AskResponse(
        session_id=chat_session.id,
        answer=assistant_msg.content,
        user_message=MessageOut.model_validate(user_msg),
        assistant_message=MessageOut.model_validate(assistant_msg),
    )


@chat_router.get("/sessions", response_model=list[ChatSessionOut])
async def my_sessions(
    account: Annotated[Account, Depends(get_current_account)],
    session: AsyncSession = Depends(get_session),
) -> list[ChatSessionOut]:
    """List the current user's chat threads (newest first)."""
    sessions = await service.list_sessions(session, account.id)
    return [ChatSessionOut.model_validate(s) for s in sessions]


@chat_router.get(
    "/sessions/{session_id}/messages", response_model=list[MessageOut]
)
async def session_messages(
    session_id: UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: AsyncSession = Depends(get_session),
) -> list[MessageOut]:
    """Return every message of one of the user's own sessions."""
    messages = await service.list_messages(session, account.id, session_id)
    return [MessageOut.model_validate(m) for m in messages]


# ----- Admin ----- #
@admin_router.get(
    "/accounts",
    response_model=list[AccountOut],
    dependencies=[Depends(require_admin)],
)
async def all_accounts(
    session: AsyncSession = Depends(get_session),
) -> list[AccountOut]:
    """Admin: list all accounts."""
    accounts = await service.list_accounts(session)
    return [AccountOut.model_validate(a) for a in accounts]


@admin_router.patch("/accounts/{account_id}/role", response_model=AccountOut)
async def change_role(
    account_id: UUID,
    payload: UpdateRoleRequest,
    _admin: Annotated[Account, Depends(require_admin)],
    session: AsyncSession = Depends(get_session),
) -> AccountOut:
    """Admin: change a target account's role (xodim/admin)."""
    account = await service.update_account_role(
        session, account_id, payload.role.value
    )
    return AccountOut.model_validate(account)


# Single router that presentation.py mounts under /v1.
router = APIRouter()
router.include_router(auth_router)
router.include_router(chat_router)
router.include_router(admin_router)

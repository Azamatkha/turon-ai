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

import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.core.ai.dependencies import get_ai_client
from src.core.ai.embeddings import OllamaEmbedder, get_embedder
from src.core.ai.interfaces import BaseAIClient
from src.core.schemas import SuccessResponse
from src.core.vectorstore.dependencies import get_vector_store
from src.core.vectorstore.qdrant_store import QdrantStore
from src.knowledge.schemas import AnswerResult, QuestionRequest
from src.knowledge.usecases import AnswerQuestionUseCase
from src.user.auth.dependencies import get_current_user
from src.user.models import User
from src.chat.schemas import (
    AddMessageModel,
    CreateSessionModel,
    GenerateTitleRequest,
    GenerateTitleResult,
    MessageView,
    PinSessionModel,
    RenameSessionModel,
    SessionDetailView,
    SessionView,
    VoteMessageModel,
)
from src.chat.usecases import (
    AddMessageUseCase,
    CreateSessionUseCase,
    DeleteMessageUseCase,
    DeleteSessionUseCase,
    GenerateTitleUseCase,
    GetSessionUseCase,
    ListSessionsUseCase,
    PinSessionUseCase,
    RenameSessionUseCase,
    VoteMessageUseCase,
    get_add_message_use_case,
    get_create_session_use_case,
    get_delete_message_use_case,
    get_delete_session_use_case,
    get_generate_title_use_case,
    get_get_session_use_case,
    get_list_sessions_use_case,
    get_pin_session_use_case,
    get_rename_session_use_case,
    get_vote_message_use_case,
)

router = APIRouter()


@router.post("/title", response_model=GenerateTitleResult)
async def generate_title(
    data: GenerateTitleRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[GenerateTitleUseCase, Depends(get_generate_title_use_case)],
) -> GenerateTitleResult:
    """Birinchi xabar matnidan Qwen orqali qisqa suhbat sarlavhasi yasaydi."""
    return await use_case.execute(text=data.text)


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


@router.patch("/sessions/{session_id}/pin", response_model=SessionView)
async def pin_session(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    data: PinSessionModel,
    use_case: Annotated[PinSessionUseCase, Depends(get_pin_session_use_case)],
) -> SessionView:
    """Suhbatni ro'yxat tepasiga qadash (pin) yoki qadamasdan qo'yish."""
    return await use_case.execute(
        user_id=current_user.id, session_id=session_id, is_pinned=data.is_pinned
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


@router.delete(
    "/sessions/{session_id}/messages/{message_id}", response_model=SuccessResponse
)
async def delete_message(
    session_id: UUID,
    message_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[DeleteMessageUseCase, Depends(get_delete_message_use_case)],
) -> SuccessResponse:
    """Xabarni o'chirish (masalan regenerate qilinganda eski javob o'chiriladi)."""
    return await use_case.execute(
        user_id=current_user.id, session_id=session_id, message_id=message_id
    )


@router.patch(
    "/sessions/{session_id}/messages/{message_id}/vote", response_model=MessageView
)
async def vote_message(
    session_id: UUID,
    message_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    data: VoteMessageModel,
    use_case: Annotated[VoteMessageUseCase, Depends(get_vote_message_use_case)],
) -> MessageView:
    """Xabarga baho berish (like/dislike): vote = 'up' | 'down' | null."""
    return await use_case.execute(
        user_id=current_user.id,
        session_id=session_id,
        message_id=message_id,
        vote=data.vote,
    )


@router.post("/ask", response_model=AnswerResult)
async def ask(
    data: QuestionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    embedder: Annotated[OllamaEmbedder, Depends(get_embedder)],
    store: Annotated[QdrantStore, Depends(get_vector_store)],
    ai_client: Annotated[BaseAIClient, Depends(get_ai_client)],
) -> AnswerResult:
    """Xodim savoli -> Qdrant qidiruv -> Qwen javob (RAG)."""
    use_case = AnswerQuestionUseCase(
        embedder=embedder, store=store, ai_client=ai_client
    )
    return await use_case.execute(question=data.question, history=data.history)


@router.post("/ask/stream")
async def ask_stream(
    data: QuestionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    embedder: Annotated[OllamaEmbedder, Depends(get_embedder)],
    store: Annotated[QdrantStore, Depends(get_vector_store)],
    ai_client: Annotated[BaseAIClient, Depends(get_ai_client)],
) -> StreamingResponse:
    """Xuddi /ask kabi, lekin javobni token-token (SSE oqim) qaytaradi —
    frontend real vaqtda matn va token sonini ko'rsatishi uchun."""
    use_case = AnswerQuestionUseCase(
        embedder=embedder, store=store, ai_client=ai_client
    )

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for ev in use_case.execute_stream(
                question=data.question, history=data.history
            ):
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001 - oqim uzilsa, xatoni klientga yuboramiz
            payload = {"type": "error", "message": str(exc)}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

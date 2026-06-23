from typing import Annotated

from fastapi import APIRouter, Depends

from src.ask.dependencies import get_ask_service
from src.ask.schemas import AskRequest, AskResponse
from src.ask.service import AskService
from src.simple_auth.dependencies import get_current_user
from src.user.models import User

router = APIRouter()


@router.post("", response_model=AskResponse)
async def ask(
    payload: AskRequest,
    service: Annotated[AskService, Depends(get_ask_service)],
    _: Annotated[User, Depends(get_current_user)],
) -> AskResponse:
    """Savol berish: RAG orqali topilgan hujjatlar asosida AI javob qaytaradi."""
    natija = await service.savol_ber(payload.savol, top_k=payload.top_k)
    return AskResponse(**natija)

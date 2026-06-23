from fastapi import Depends

from src.ask.service import AskService
from src.core.ai.dependencies import get_ai_client
from src.core.ai.interfaces import BaseAIClient


def get_ask_service(
    ai_client: BaseAIClient = Depends(get_ai_client),
) -> AskService:
    return AskService(ai_client)

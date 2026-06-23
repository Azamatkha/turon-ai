from fastapi import Depends
import httpx

from src.core.ai.factory import AIClientFactory
from src.core.ai.interfaces import BaseAIClient
from src.core.http.dependencies import get_http_client
from src.main.config import config


def get_ai_client(
    http: httpx.AsyncClient = Depends(get_http_client),
) -> BaseAIClient:
    provider = config.ai.AI_PROVIDER
    return AIClientFactory.create(name=provider, http=http)

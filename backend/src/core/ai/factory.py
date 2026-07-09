import httpx

from src.core.ai.clients.ollama import OllamaClient
from src.core.ai.interfaces import BaseAIClient
from src.core.errors.exceptions import InfrastructureException


class AIClientFactory:

    _clients = {"ollama": OllamaClient}

    @classmethod
    def create(cls, name: str, http: httpx.AsyncClient) -> BaseAIClient:
        client_class = cls._clients.get(name.lower())
        if not client_class:
            raise InfrastructureException(f"Unsupported client: {name}")
        return client_class(http=http)

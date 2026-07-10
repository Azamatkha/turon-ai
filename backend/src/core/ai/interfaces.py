from abc import ABC, abstractmethod
from typing import Any

from src.core.ai.schemas import CallResult, DiagnosticResponse, TextGenResult


class BaseAIClient(ABC):

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        *,
        temperature: float | None = None,
        max_tokens: int,
        system_prompt: str | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def generate_text_with_usage(
        self,
        prompt: str,
        *,
        temperature: float | None = None,
        max_tokens: int,
        system_prompt: str | None = None,
    ) -> TextGenResult:
        """generate_text bilan bir xil, lekin token statistikasini ham qaytaradi
        (debug: javob token yetishmovchiligidan kesilib qolganini bilish uchun)."""
        raise NotImplementedError

    @abstractmethod
    async def generate_json(
        self,
        prompt: str | list[dict[str, Any]],
        schema: dict[str, Any] | None = None,
        *,
        temperature: float | None = None,
        max_tokens: int,
        system_prompt: str | None = None,
    ) -> CallResult:
        raise NotImplementedError

    @abstractmethod
    async def ping(self) -> DiagnosticResponse:
        raise NotImplementedError

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
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
        think: bool = False,
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
        think: bool = False,
    ) -> TextGenResult:
        """generate_text bilan bir xil, lekin token statistikasini ham qaytaradi
        (debug: javob token yetishmovchiligidan kesilib qolganini bilish uchun).

        `think=True` — reasoning modelga mulohaza yuritishga ruxsat beradi.
        Bunda max_tokens kattaroq bo'lishi kerak: limit mulohaza va javob
        o'rtasida bo'linadi."""
        raise NotImplementedError

    def stream_generate(
        self,
        prompt: str,
        *,
        temperature: float | None = None,
        max_tokens: int,
        system_prompt: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Javobni oqim (token-token) tarzida qaytaradi. Har bir provayder
        qo'llab-quvvatlamasligi mumkin — standart holatda amalga oshirilmagan."""
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
        think: bool = False,
    ) -> CallResult:
        raise NotImplementedError

    @abstractmethod
    async def ping(self) -> DiagnosticResponse:
        raise NotImplementedError

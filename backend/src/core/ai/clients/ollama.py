import json
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from loggers import get_logger
from src.core.ai.interfaces import BaseAIClient
from src.core.ai.parsing import extract_json
from src.core.ai.prompts import DIAGNOSTIC_PROMPT, DIAGNOSTIC_SYSTEM
from src.core.ai.schemas import (
    AttemptInfo,
    CallResult,
    DiagnosticResponse,
    TextGenResult,
)
from src.core.errors.exceptions import InfrastructureException
from src.core.patterns.singleton import singleton
from src.main.config import config

logger = get_logger(__name__)


@singleton
class OllamaClient(BaseAIClient):
    def __init__(self, http: httpx.AsyncClient) -> None:
        self.base_url = config.ai.OLLAMA_BASE_URL.rstrip("/")
        self.model = config.ai.OLLAMA_MODEL
        self.num_ctx = config.ai.OLLAMA_NUM_CTX
        self.timeout = config.ai.TIMEOUT_SECONDS
        self.default_temperature = config.ai.DEFAULT_TEMPERATURE
        self.http = http

    # ----- helpers ----- #
    @staticmethod
    def _build_messages(
        prompt: str, system_prompt: str | None
    ) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def _chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float | None,
        max_tokens: int,
    ) -> dict[str, Any]:
        # Ollama'ning o'ziga xos (native) /api/chat endpointi — OpenAI-uyg'un
        # /v1/chat/completions'dan farqli, "think": false'ni ishonchli va
        # kafolatli qo'llab-quvvatlaydi (reasoning modellarni o'ylashsiz javobga
        # majburlaydi, aks holda butun token limiti "o'ylashga" ketib qolardi).
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {
                "temperature": (
                    temperature
                    if temperature is not None
                    else self.default_temperature
                ),
                "num_predict": max_tokens,
                # Kontekst oynasini aniq belgilaymiz — aks holda Ollama standart
                # 2048'da RAG kontekst + system prompt'ni oldidan kesib tashlaydi.
                "num_ctx": self.num_ctx,
            },
        }
        try:
            resp = await self.http.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise InfrastructureException(f"Ollama connection error: {exc}") from exc

        if resp.status_code != 200:
            raise InfrastructureException(
                f"Ollama error {resp.status_code}: {resp.text[:200]}"
            )
        data: dict[str, Any] = resp.json()
        return data

    @staticmethod
    def _first_text(data: dict[str, Any]) -> str:
        message = data.get("message") or {}
        return str(message.get("content", ""))

    # ----- interface ----- #
    async def generate_text(
        self,
        prompt: str,
        *,
        temperature: float | None = None,
        max_tokens: int,
        system_prompt: str | None = None,
    ) -> str:
        result = await self.generate_text_with_usage(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
        )
        return result.text

    async def generate_text_with_usage(
        self,
        prompt: str,
        *,
        temperature: float | None = None,
        max_tokens: int,
        system_prompt: str | None = None,
    ) -> TextGenResult:
        messages = self._build_messages(prompt, system_prompt)
        data = await self._chat(messages, temperature, max_tokens)

        return TextGenResult(
            text=self._first_text(data),
            finish_reason=str(data.get("done_reason", "")),
            prompt_tokens=int(data.get("prompt_eval_count", 0)),
            completion_tokens=int(data.get("eval_count", 0)),
            max_tokens=max_tokens,
        )

    async def stream_generate(
        self,
        prompt: str,
        *,
        temperature: float | None = None,
        max_tokens: int,
        system_prompt: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Javobni token-token (oqim) qaytaradi — real vaqtda ko'rsatish uchun.
        Har bir bo'lak: {"type": "delta", "text": ...}; oxirida:
        {"type": "done", "completion_tokens": N, "finish_reason": ...}."""
        messages = self._build_messages(prompt, system_prompt)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "think": False,
            "options": {
                "temperature": (
                    temperature
                    if temperature is not None
                    else self.default_temperature
                ),
                "num_predict": max_tokens,
                "num_ctx": self.num_ctx,
            },
        }
        try:
            async with self.http.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            ) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    raise InfrastructureException(
                        f"Ollama error {resp.status_code}: {body[:200]!r}"
                    )
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    message = data.get("message") or {}
                    delta = str(message.get("content", ""))
                    if delta:
                        yield {"type": "delta", "text": delta}
                    if data.get("done"):
                        yield {
                            "type": "done",
                            "completion_tokens": int(data.get("eval_count", 0)),
                            "finish_reason": str(data.get("done_reason", "stop")),
                        }
        except httpx.HTTPError as exc:
            raise InfrastructureException(f"Ollama connection error: {exc}") from exc

    async def generate_json(
        self,
        prompt: str | list[dict[str, Any]],
        schema: dict[str, Any] | None = None,
        *,
        temperature: float | None = None,
        max_tokens: int,
        system_prompt: str | None = None,
    ) -> CallResult:
        if isinstance(prompt, list):
            messages: list[dict[str, Any]] = list(prompt)
            if system_prompt:
                messages.insert(0, {"role": "system", "content": system_prompt})
        else:
            messages = self._build_messages(prompt, system_prompt)

        data = await self._chat(messages, temperature, max_tokens)
        text = self._first_text(data)
        try:
            parsed: Any = json.loads(extract_json(text))
        except (json.JSONDecodeError, ValueError):
            parsed = {"raw": text}

        return CallResult(
            data=parsed,
            used_model=self.model,
            fallback_used=False,
            total_attempts=1,
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            },
            model=self.model,
            model_chain=[self.model],
            attempts=[
                AttemptInfo(model=self.model, attempt=1, ok=True, status=200)
            ],
        )

    async def ping(self) -> DiagnosticResponse:
        start = time.perf_counter()
        messages = self._build_messages(DIAGNOSTIC_PROMPT, DIAGNOSTIC_SYSTEM)
        try:
            data = await self._chat(messages, 0.0, 64)
        except InfrastructureException as exc:
            latency = int((time.perf_counter() - start) * 1000)
            return DiagnosticResponse(
                ok=False,
                latency_ms=latency,
                used_model=self.model,
                fallback_used=False,
                total_attempts=1,
                model_chain=[self.model],
                attempts=[
                    AttemptInfo(
                        model=self.model,
                        attempt=1,
                        ok=False,
                        error_type=str(exc),
                    )
                ],
                response=None,
            )

        latency = int((time.perf_counter() - start) * 1000)
        text = self._first_text(data)
        try:
            response_obj: dict[str, Any] | None = json.loads(extract_json(text))
        except (json.JSONDecodeError, ValueError):
            response_obj = {"raw": text}

        return DiagnosticResponse(
            ok=True,
            latency_ms=latency,
            used_model=self.model,
            fallback_used=False,
            total_attempts=1,
            model_chain=[self.model],
            attempts=[AttemptInfo(model=self.model, attempt=1, ok=True, status=200)],
            response=response_obj,
        )

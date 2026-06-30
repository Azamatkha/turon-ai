import asyncio
from dataclasses import dataclass, field
import json
import random
import time
from typing import Any

import httpx

from loggers import get_logger
from src.core.ai.interfaces import BaseAIClient
from src.core.ai.parsing import detect_deprecated_param, extract_json
from src.core.ai.prompts import DIAGNOSTIC_PROMPT, DIAGNOSTIC_SYSTEM
from src.core.ai.schemas import AttemptInfo, CallResult, DiagnosticResponse
from src.core.errors.exceptions import InfrastructureException
from src.core.patterns.singleton import singleton
from src.main.config import config

logger = get_logger(__name__)


@dataclass
class _RawCallResult:
    data: Any
    used_model: str
    fallback_used: bool
    total_attempts: int
    model_chain: list[str]
    attempts: list[AttemptInfo] = field(default_factory=list)


@singleton
class AnthropicClient(BaseAIClient):
    def __init__(self, http: httpx.AsyncClient) -> None:
        self.api_key = config.ai.ANTHROPIC_API_KEY
        self.base_url = config.ai.ANTHROPIC_BASE_URL
        self.api_version = config.ai.ANTHROPIC_VERSION
        self.max_retries = config.ai.MAX_RETRIES
        self.http = http

        self.model_chain = self._resolve_model_chain(
            config.ai.ANTHROPIC_MODEL, config.ai.ANTHROPIC_FALLBACK_MODELS
        )
        self.base_delay: float = 1.0
        self.max_jitter: float = 0.5
        self._deprecated_params: dict[str, set[str]] = {}

    @staticmethod
    def _resolve_model_chain(primary: str, fallbacks: list[str]) -> list[str]:
        chain = [primary, *fallbacks]
        return list(dict.fromkeys(m for m in chain if m))

    async def generate_text(
        self,
        prompt: str,
        *,
        temperature: float | None = None,
        max_tokens: int,
        system_prompt: str | None = None,
    ) -> str:
        result = await self._call_with_fallback(
            system_prompt=system_prompt,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return self._first_text_block(result.data)

    async def generate_json(
        self,
        prompt: str | list[dict[str, Any]],
        schema: dict[str, Any] | None = None,
        *,
        temperature: float | None = None,
        max_tokens: int,
        system_prompt: str | None = None,
    ) -> CallResult:
        result = await self._call_with_fallback(
            system_prompt=system_prompt,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            schema=schema,
        )

        stop = result.data.get("stop_reason")
        if stop == "refusal":
            logger.error("[AI] Anthropic refused the request")
            raise InfrastructureException("AI refused the request.")
        if stop == "max_tokens":
            logger.error("[AI] Anthropic response truncated at max_tokens")
            raise InfrastructureException("AI response truncated (max_tokens).")

        usage = result.data.get("usage", {})
        model = result.data.get("model", "")

        raw = self._first_text_block(result.data)
        try:
            parsed = json.loads(extract_json(raw))
        except json.JSONDecodeError as e:
            logger.error("[AI] Anthropic returned invalid JSON")
            raise InfrastructureException("Invalid JSON from AI") from e

        return CallResult(
            data=parsed,
            used_model=result.used_model,
            fallback_used=result.fallback_used,
            total_attempts=result.total_attempts,
            model_chain=result.model_chain,
            attempts=result.attempts,
            usage=result.data.get("usage", {}),
            model=result.data.get("model", ""),
        )

    async def ping(self) -> DiagnosticResponse:
        start = time.monotonic()
        result = await self._call_with_fallback(
            prompt=DIAGNOSTIC_PROMPT,
            system_prompt=DIAGNOSTIC_SYSTEM,
            schema=None,
            max_tokens=64,
        )
        return DiagnosticResponse(
            ok=True,
            latency_ms=int((time.monotonic() - start) * 1000),
            used_model=result.used_model,
            fallback_used=result.fallback_used,
            total_attempts=result.total_attempts,
            model_chain=result.model_chain,
            attempts=result.attempts,
            response=result.data,
        )

    async def _call_with_fallback(
        self,
        *,
        system_prompt: str | None = None,
        prompt: str | list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int,
        schema: dict[str, Any] | None = None,
    ) -> _RawCallResult:
        chain = self.model_chain
        total_attempts = 0
        attempts: list[AttemptInfo] = []
        last_error: Exception | None = None

        for model in chain:
            dep_params = self._deprecated_params.setdefault(model, set())
            attempt = 0
            while attempt <= self.max_retries:
                total_attempts += 1
                body = self._build_body(
                    model=model,
                    system_prompt=system_prompt,
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    dep_params=dep_params,
                    schema=schema,
                )

                try:
                    resp = await self.http.post(
                        self.base_url,
                        headers=self._build_headers(),
                        json=body,
                        timeout=300,
                    )
                except httpx.HTTPError as e:
                    logger.error(
                        "[AI][%s] network error: %s %s",
                        model,
                        type(e).__name__,
                        repr(e),
                    )
                    break

                if resp.is_success:
                    attempts.append(
                        AttemptInfo(
                            model=model,
                            attempt=attempt,
                            ok=True,
                            status=resp.status_code,
                            error_type=None,
                        )
                    )
                    data: dict[str, Any] = resp.json()
                    if model != chain[0]:
                        logger.warning(
                            "[AI] FALLBACK SUCCESS: %s -> %s (after %s attempts)",
                            chain[0],
                            model,
                            total_attempts,
                        )
                    return _RawCallResult(
                        data=data,
                        used_model=model,
                        fallback_used=model != chain[0],
                        total_attempts=total_attempts,
                        model_chain=chain,
                        attempts=attempts,
                    )

                error_body = resp.text
                try:
                    error_type: str | None = (
                        json.loads(error_body).get("error", {}).get("type")
                    )
                except (json.JSONDecodeError, ValueError):
                    error_type = None
                status = resp.status_code
                attempts.append(
                    AttemptInfo(
                        model=model,
                        attempt=attempt,
                        ok=False,
                        status=status,
                        error_type=error_type,
                    )
                )

                if status == 400 and error_type == "invalid_request_error":
                    deprecated = detect_deprecated_param(error_body)
                    if deprecated and deprecated not in dep_params:
                        dep_params.add(deprecated)
                        logger.warning(
                            "[AI][%s] param '%s' deprecated — retrying without it",
                            model,
                            deprecated,
                        )
                        continue

                last_error = InfrastructureException(
                    f"Anthropic {status}: {error_body[:200]}"
                )
                if status == 429 or error_type == "rate_limit_error":
                    retry_after = self._parse_retry_after(resp)
                    if retry_after:
                        logger.warning(
                            "[AI][%s] rate limited, retry-after: %ss",
                            model,
                            retry_after,
                        )

                if self._is_retryable(status, error_type):
                    if attempt < self.max_retries:
                        await asyncio.sleep(self._backoff(attempt))
                        attempt += 1
                        continue
                    logger.warning("[AI][%s] exhausted — next model", model)
                    break

                logger.error(
                    "[AI][%s] non-retryable %s %s", model, status, error_type or ""
                )
                raise last_error

        logger.error("[AI] ALL models exhausted (%s)", " -> ".join(chain))
        raise last_error or InfrastructureException("AI provider error.")

    def _build_headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
            "content-type": "application/json",
        }

    def _build_body(
        self,
        *,
        model: str,
        system_prompt: str | None,
        prompt: str | list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int,
        dep_params: set[str],
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            body["system"] = system_prompt
        if temperature is not None and "temperature" not in dep_params:
            body["temperature"] = temperature
        if schema:
            body["output_config"] = {
                "format": {"type": "json_schema", "schema": schema}
            }
        return body

    def _backoff(self, attempt: int) -> float:
        delay = self.base_delay * (2**attempt) + random.uniform(0, self.max_jitter)
        return float(delay)

    @staticmethod
    def _first_text_block(data: dict[str, Any]) -> str:
        for block in data.get("content", []):
            if block.get("type") == "text":
                return str(block.get("text", ""))
        logger.error("[AI] No text block in Anthropic response")
        raise InfrastructureException("AI returned no text block.")

    @staticmethod
    def _is_retryable(status: int, error_type: str | None) -> bool:
        return (
            status == 529
            or error_type == "overloaded_error"
            or status == 429
            or error_type == "rate_limit_error"
            or 500 <= status < 600
        )

    @staticmethod
    def _parse_retry_after(resp: httpx.Response) -> int | None:
        value = resp.headers.get("retry-after")
        return int(value) if value and value.isdigit() else None

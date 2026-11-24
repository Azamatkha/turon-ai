import base64
from collections.abc import AsyncIterator
import json
import time
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
    ToolCall,
    ToolTurn,
)
from src.core.errors.exceptions import InfrastructureException
from src.core.patterns.singleton import singleton
from src.main.config import config

logger = get_logger(__name__)


def ollama_error_message(status: int, body: str, model: str) -> str:
    """Ollama HTTP xatosini logda BITTA tushunarli qatorga aylantiradi.

    Model serverda yo'q bo'lsa (nomi .env da xato yoki `ollama pull`
    qilinmagan) Ollama 404 + {"error": "model ... not found"} qaytaradi.
    Ilgari xom javob tanasi (bytes repr) traceback bilan birga chiqardi va
    asl sabab — "model yo'q" — ko'rinmay qolardi."""
    try:
        detail = str(json.loads(body).get("error", "")) or body
    except (ValueError, AttributeError):
        detail = body
    detail = " ".join(detail.split())[:200]
    if status == 404 and "not found" in detail.lower():
        return (
            f"Ollama modeli topilmadi: {model!r} — .env dagi nomni tekshiring "
            f"yoki Ollama serverida `ollama pull {model}` qiling"
        )
    return f"Ollama error {status}: {detail}"


@singleton
class OllamaClient(BaseAIClient):
    def __init__(self, http: httpx.AsyncClient) -> None:
        self.base_url = config.ai.OLLAMA_BASE_URL.rstrip("/")
        self.model = config.ai.OLLAMA_MODEL
        self.num_ctx = config.ai.OLLAMA_NUM_CTX
        self.min_num_ctx = config.ai.OLLAMA_MIN_NUM_CTX
        self.send_num_ctx = config.ai.OLLAMA_SEND_NUM_CTX
        self.timeout = config.ai.TIMEOUT_SECONDS
        self.default_temperature = config.ai.DEFAULT_TEMPERATURE
        self.http = http
        # /api/ps keshi: (num_ctx, olingan_vaqt). Har so'rovda Ollama'ni
        # so'ramaslik uchun.
        self._ctx_cache: tuple[int, float] | None = None
        # Logni faqat qiymat O'ZGARGANDA yozamiz (har so'rovda emas)
        self._last_logged_ctx: int | None = None
        # Model rasm o'qiy oladimi (/api/show -> capabilities) — bir marta so'raladi
        self._vision: bool | None = None

    # /api/ps natijasi shuncha soniya ishlatiladi
    CTX_CACHE_TTL = 10.0
    CTX_PROBE_TIMEOUT = 2.0

    # ----- helpers ----- #
    async def _loaded_ctx(self) -> int:
        """Serverda model HOZIR qaysi oyna bilan yuklangan (/api/ps).
        Yuklanmagan yoki aniqlab bo'lmasa — 0. Natija CTX_CACHE_TTL keshlanadi."""
        now = time.monotonic()
        if self._ctx_cache and now - self._ctx_cache[1] < self.CTX_CACHE_TTL:
            return self._ctx_cache[0]
        loaded = 0
        try:
            resp = await self.http.get(
                f"{self.base_url}/api/ps", timeout=self.CTX_PROBE_TIMEOUT
            )
            if resp.status_code == 200:
                for m in resp.json().get("models") or []:
                    if self.model in (m.get("name"), m.get("model")):
                        loaded = int(m.get("context_length") or 0)
                        break
        except (httpx.HTTPError, ValueError, TypeError):
            # Tekshiruv ixtiyoriy — xato bo'lsa "noma'lum" deb davom etamiz
            pass
        self._ctx_cache = (loaded, now)
        if loaded and loaded != self._last_logged_ctx:
            log = logger.warning if loaded < self.min_num_ctx else logger.info
            log("Ollama modeli %d kontekst bilan ishlayapti (minimum: %d)", loaded, self.min_num_ctx)
            self._last_logged_ctx = loaded
        return loaded

    async def _resolve_num_ctx(self) -> int | None:
        """So'rovga num_ctx yuborish kerakmi va qaysi.

        Bu loyiha oynani O'ZI BELGILAMAYDI. Ollama serveridan boshqa
        loyihalar ham foydalanadi (65536 bilan) va bitta model bir vaqtda faqat
        BITTA oyna bilan turadi: boshqa qiymat so'ralsa, 122B model VRAM'dan
        chiqarilib qayta yuklanadi (~60 s). Ilgari model yuklanmagan paytda biz
        config'dagi 32768 ni yuborardik — model 32k bilan ochilib, keyin boshqa
        loyiha uni yana 65k ga qayta yuklardi.

        Endi:
        * model yuklangan — AYNAN o'sha oyna yuboriladi (qayta yuklanmaydi;
          num_ctx umuman yuborilmasa Ollama standart qiymatni qo'yib, modelni
          qayta yuklab yuborishi mumkin — 2026-11-11 hodisasi);
        * yuklanmagan / noma'lum — num_ctx YUBORILMAYDI: Ollama serverdagi
          sozlama (OLLAMA_CONTEXT_LENGTH) bilan ochadi;
        * yuklangan oyna promptlarimizga juda kichik (< OLLAMA_MIN_NUM_CTX) —
          faqat shunda minimum so'raladi, aks holda system prompt kesiladi."""
        loaded = await self._loaded_ctx()
        if not loaded:
            return None
        return max(loaded, self.min_num_ctx)

    async def _options(self, temperature: float | None, max_tokens: int) -> dict[str, Any]:
        """So'rov `options` bloki. num_ctx faqat model allaqachon yuklangan
        bo'lsa (o'sha qiymat) qo'shiladi — qara: _resolve_num_ctx."""
        opts: dict[str, Any] = {
            "temperature": (
                temperature if temperature is not None else self.default_temperature
            ),
            "num_predict": max_tokens,
        }
        if self.send_num_ctx:
            num_ctx = await self._resolve_num_ctx()
            if num_ctx:
                opts["num_ctx"] = num_ctx
        else:
            # Hech qachon yuborilmaydi — faqat kichik oyna haqida ogohlantirish
            await self._loaded_ctx()
        return opts

    async def context_window(self) -> int | None:
        """Model AMALDA qaysi oyna bilan ishlayapti (hujjat tahlilchisi kabi
        katta promptlar byudjetini shundan hisoblaydi). Noma'lum — None."""
        loaded = await self._loaded_ctx()
        if not loaded:
            return None
        return max(loaded, self.min_num_ctx) if self.send_num_ctx else loaded

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
        think: bool = False,
        fmt: dict[str, Any] | None = None,
        timeout: float | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        # Ollama'ning o'ziga xos (native) /api/chat endpointi — OpenAI-uyg'un
        # /v1/chat/completions'dan farqli, "think" bayrog'ini ishonchli
        # qo'llab-quvvatlaydi.
        #
        # Standart holat — think=False: aks holda butun token limiti "o'ylashga"
        # ketib, javob kesilib qolardi. Lekin savolni TUSHUNISH bosqichida
        # (router) o'ylash yoqiladi — o'sha yerda chiqish qisqa va aynan
        # mulohaza kerak. think=True bo'lganda chaqiruvchi max_tokens'ni
        # oshirishi shart: limit mulohaza + javobga birga taqsimlanadi.
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": think,
            # keep_alive ATAYLAB yuborilmaydi: model xotirada qancha turishini
            # Ollama serverining o'z sozlamasi (OLLAMA_KEEP_ALIVE) belgilaydi.
            "options": await self._options(temperature, max_tokens),
        }
        # JSON sxema berilsa — Ollama chiqishni STRUKTURA bo'yicha majburlaydi.
        # Ilgari sxema qabul qilinardi-yu, so'rovga umuman qo'shilmasdi: model
        # xohlagan ko'rinishda javob berardi va parser uni topa olmay qolardi.
        if fmt is not None:
            payload["format"] = fmt
        # Tool-calling: model shu ro'yxatdan asbob chaqirishi mumkin
        if tools:
            payload["tools"] = tools
        try:
            resp = await self.http.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=timeout if timeout is not None else self.timeout,
            )
        except httpx.HTTPError as exc:
            # httpx.ReadTimeout matni bo'sh — xato turi nomisiz logda
            # "Ollama connection error: " deb chiqib, sababi ko'rinmasdi.
            raise InfrastructureException(
                f"Ollama connection error: {type(exc).__name__} {exc}".rstrip()
            ) from exc

        if resp.status_code != 200:
            raise InfrastructureException(
                ollama_error_message(resp.status_code, resp.text, self.model)
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
        think: bool = False,
    ) -> str:
        result = await self.generate_text_with_usage(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            think=think,
        )
        return result.text

    async def generate_text_with_usage(
        self,
        prompt: str,
        *,
        temperature: float | None = None,
        max_tokens: int,
        system_prompt: str | None = None,
        think: bool = False,
    ) -> TextGenResult:
        messages = self._build_messages(prompt, system_prompt)
        data = await self._chat(messages, temperature, max_tokens, think=think)

        return TextGenResult(
            text=self._first_text(data),
            finish_reason=str(data.get("done_reason", "")),
            prompt_tokens=int(data.get("prompt_eval_count", 0)),
            completion_tokens=int(data.get("eval_count", 0)),
            max_tokens=max_tokens,
        )

    @staticmethod
    def _tool_calls(message: dict[str, Any]) -> list[ToolCall]:
        """Ollama `message.tool_calls` ni o'qiydi. Argumentlar ba'zan JSON
        satr bo'lib keladi — lug'atga aylantiriladi; buzuq bo'lsa bo'sh."""
        calls: list[ToolCall] = []
        for raw in message.get("tool_calls") or []:
            fn = (raw or {}).get("function") or {}
            name = str(fn.get("name") or "").strip()
            if not name:
                continue
            args = fn.get("arguments")
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except ValueError:
                    args = {}
            calls.append(ToolCall(name=name, arguments=args if isinstance(args, dict) else {}))
        return calls

    async def chat_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        *,
        temperature: float | None = None,
        max_tokens: int,
        timeout: float | None = None,
    ) -> ToolTurn:
        data = await self._chat(
            messages, temperature, max_tokens, think=False, timeout=timeout, tools=tools
        )
        message = dict(data.get("message") or {})
        return ToolTurn(
            content=str(message.get("content", "")),
            tool_calls=self._tool_calls(message),
            message=message,
            prompt_tokens=int(data.get("prompt_eval_count", 0)),
            completion_tokens=int(data.get("eval_count", 0)),
            finish_reason=str(data.get("done_reason", "")),
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
            "options": await self._options(temperature, max_tokens),
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
                        ollama_error_message(
                            resp.status_code,
                            body.decode("utf-8", "replace"),
                            self.model,
                        )
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
            raise InfrastructureException(
                f"Ollama connection error: {type(exc).__name__} {exc}".rstrip()
            ) from exc

    async def generate_json(
        self,
        prompt: str | list[dict[str, Any]],
        schema: dict[str, Any] | None = None,
        *,
        temperature: float | None = None,
        max_tokens: int,
        system_prompt: str | None = None,
        think: bool = False,
        timeout: float | None = None,
    ) -> CallResult:
        if isinstance(prompt, list):
            messages: list[dict[str, Any]] = list(prompt)
            if system_prompt:
                messages.insert(0, {"role": "system", "content": system_prompt})
        else:
            messages = self._build_messages(prompt, system_prompt)

        data = await self._chat(
            messages,
            temperature,
            max_tokens,
            think=think,
            fmt=schema,
            timeout=timeout,
        )
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

    async def supports_vision(self) -> bool:
        """Ollama'dagi model "vision" imkoniyatiga egami (/api/show).

        Javob keshlanadi. Ollama javob bermasa — keshlanmaydi va False
        qaytadi: chaqiruvchi eski yo'lga (OCR) o'tadi, keyingi safar qayta
        so'raladi."""
        if self._vision is not None:
            return self._vision
        try:
            resp = await self.http.post(
                f"{self.base_url}/api/show",
                json={"model": self.model},
                timeout=self.CTX_PROBE_TIMEOUT * 5,
            )
            if resp.status_code != 200:
                return False
            caps = resp.json().get("capabilities") or []
        except (httpx.HTTPError, ValueError, AttributeError):
            return False
        self._vision = "vision" in caps
        logger.info("Ollama modeli %r vision: %s", self.model, self._vision)
        return self._vision

    async def read_image(
        self,
        image_png: bytes,
        *,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int,
        timeout: float | None = None,
    ) -> TextGenResult:
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append(
            {
                "role": "user",
                "content": prompt,
                # Ollama rasmni base64 ko'rinishida `images` maydonida oladi
                "images": [base64.b64encode(image_png).decode("ascii")],
            }
        )
        data = await self._chat(messages, 0.0, max_tokens, timeout=timeout)
        return TextGenResult(
            text=self._first_text(data),
            finish_reason=str(data.get("done_reason", "")),
            prompt_tokens=int(data.get("prompt_eval_count", 0)),
            completion_tokens=int(data.get("eval_count", 0)),
            max_tokens=max_tokens,
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

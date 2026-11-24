from typing import Any

from src.core.schemas import Base


class AttemptInfo(Base):
    model: str
    attempt: int
    ok: bool
    status: int | None = None
    error_type: str | None = None


class DiagnosticResponse(Base):
    ok: bool
    latency_ms: int
    used_model: str
    fallback_used: bool
    total_attempts: int
    model_chain: list[str]
    attempts: list[AttemptInfo]
    response: dict[str, Any] | None = None


class CallResult(Base):
    data: Any
    used_model: str
    fallback_used: bool
    total_attempts: int
    usage: dict[str, Any] = {}
    model: str = ""
    model_chain: list[str] = []
    attempts: list[AttemptInfo] = []


class TextGenResult(Base):
    """generate_text natijasi + debug uchun token statistikasi.

    finish_reason == "length" bo'lsa — javob max_tokens tugagani sabab
    kesilib qolgan bo'lishi mumkin (masalan qwen ko'p "o'ylab" joy qoldirmagan).
    """

    text: str
    finish_reason: str
    prompt_tokens: int
    completion_tokens: int
    max_tokens: int


class ToolCall(Base):
    """Model chaqirmoqchi bo'lgan bitta asbob (tool-calling)."""

    name: str
    arguments: dict[str, Any] = {}


class ToolTurn(Base):
    """chat_tools natijasi: model yo matn yozdi, yo asbob(lar) chaqirdi.

    `message` — modelning xom javob xabari: keyingi qadamda suhbatga AYNAN
    shunday qaytariladi (Ollama tool_calls'ni shu xabardan taniydi)."""

    content: str
    tool_calls: list[ToolCall] = []
    message: dict[str, Any] = {}
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str = ""

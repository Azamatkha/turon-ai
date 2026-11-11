from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from src.core.schemas import Base

ALLOWED_ROLES = {"user", "assistant"}


class SessionView(Base):
    id: UUID
    title: str
    is_pinned: bool
    created_at: datetime
    updated_at: datetime
    # Tarjimon rejimi: None | "pending" | "en" | "ru" | "uz" | "uz_cyrl"
    translate_lang: str | None = None


class SourceItem(Base):
    """Javob tayangan hujjat: sarlavha va o'xshashlik bali."""

    title: str = Field(..., max_length=500)
    score: float = 0.0
    # Veb-qidiruvdan olingan manba: havola va kind="web"
    url: str | None = Field(None, max_length=1000)
    kind: str = Field("kb", max_length=10)


class MessageView(Base):
    id: UUID
    role: str
    content: str
    created_at: datetime
    vote: str | None = None
    # Faqat assistant xabarida (qara: ChatMessage.completion_tokens)
    completion_tokens: int | None = None
    finish_reason: str | None = None
    sources: list[SourceItem] | None = None


class SessionDetailView(SessionView):
    messages: list[MessageView]


class CreateSessionModel(Base):
    title: str = ""


class RenameSessionModel(Base):
    title: str


class PinSessionModel(Base):
    is_pinned: bool


class AddMessageModel(Base):
    role: str
    content: str
    # Mijoz javob oqimining "done" hodisasidan oladi va xabar bilan birga
    # saqlaydi. Ixtiyoriy — eski mijozlar (mobil) yubormasa ham ishlaydi.
    completion_tokens: int | None = Field(None, ge=0)
    finish_reason: str | None = Field(None, max_length=20)
    # Javob oqimining "done" hodisasidagi manbalar (ko'pi bilan 10 ta)
    sources: list[SourceItem] | None = Field(None, max_length=10)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in ALLOWED_ROLES:
            raise ValueError("role faqat 'user' yoki 'assistant' bo'lishi mumkin")
        return value


class GenerateTitleRequest(Base):
    text: str


class GenerateTitleResult(Base):
    title: str


# Dislike sabablari (frontend tugmalari bilan bir xil)
VOTE_REASONS = {"wrong", "outdated", "incomplete", "other"}


class VoteMessageModel(Base):
    vote: str | None = None
    # Faqat vote="down" da ma'noli; boshqa holatda e'tiborsiz qoldiriladi
    reason: str | None = None
    comment: str | None = Field(None, max_length=500)

    @field_validator("vote")
    @classmethod
    def validate_vote(cls, value: str | None) -> str | None:
        if value not in (None, "up", "down"):
            raise ValueError("vote faqat 'up', 'down' yoki null bo'lishi mumkin")
        return value

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str | None:
        if value is not None and value not in VOTE_REASONS:
            raise ValueError("Noma'lum dislike sababi")
        return value


class SuggestFollowupsRequest(Base):
    question: str = Field(min_length=1, max_length=2000)
    # Javob matni modelga qisqartirib beriladi (qara: SuggestFollowupsUseCase)
    answer: str = Field(min_length=1, max_length=20000)
    # Javob tayangan hujjatlar sarlavhalari — mavzuni aniqroq ushlash uchun
    sources: list[str] = Field(default_factory=list, max_length=10)


class SuggestFollowupsResult(Base):
    suggestions: list[str]


class MessageSearchHit(Base):
    session_id: UUID
    session_title: str
    message_id: UUID
    role: str
    # Moslik atrofidagi qisqa parcha (...matn...)
    snippet: str
    created_at: datetime

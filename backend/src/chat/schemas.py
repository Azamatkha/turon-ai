from datetime import datetime
from uuid import UUID

from pydantic import field_validator

from src.core.schemas import Base

ALLOWED_ROLES = {"user", "assistant"}


class SessionView(Base):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class MessageView(Base):
    id: UUID
    role: str
    content: str
    created_at: datetime
    vote: str | None = None


class SessionDetailView(SessionView):
    messages: list[MessageView]


class CreateSessionModel(Base):
    title: str = ""


class RenameSessionModel(Base):
    title: str


class AddMessageModel(Base):
    role: str
    content: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in ALLOWED_ROLES:
            raise ValueError("role faqat 'user' yoki 'assistant' bo'lishi mumkin")
        return value


class VoteMessageModel(Base):
    vote: str | None = None

    @field_validator("vote")
    @classmethod
    def validate_vote(cls, value: str | None) -> str | None:
        if value not in (None, "up", "down"):
            raise ValueError("vote faqat 'up', 'down' yoki null bo'lishi mumkin")
        return value

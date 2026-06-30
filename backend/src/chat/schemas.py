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

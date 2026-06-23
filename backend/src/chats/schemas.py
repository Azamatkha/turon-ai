from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MessageView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    created_at: datetime


class SessionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class SessionDetail(SessionView):
    messages: list[MessageView] = []


class CreateSession(BaseModel):
    title: str = Field(default="", max_length=200)


class RenameSession(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class AddMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1)

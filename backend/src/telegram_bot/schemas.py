from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.core.schemas import Base

# Bitta so'rovdagi eng ko'p yozuv — bot shundan kattasini bo'laklab yuboradi
SYNC_BATCH_LIMIT = 1000


class _BotPayload(BaseModel):
    # Bot yangi maydon qo'shsa ham backend yiqilmasin
    model_config = ConfigDict(extra="ignore")


class BotUserIn(_BotPayload):
    telegram_id: int
    username: str = Field("", max_length=64)
    full_name: str = Field("", max_length=256)
    language: str = Field("", max_length=8)
    phone: str = Field("", max_length=32)
    reg_step: str = Field("", max_length=8)
    is_banned: bool = False
    first_seen_at: datetime
    last_message_at: datetime | None = None


class BotMessageIn(_BotPayload):
    bot_message_id: int
    # Qaysi userniki — Telegram ID orqali
    telegram_id: int
    direction: str = Field(max_length=8)
    status: str = Field(max_length=16)
    content_type: str = Field("text", max_length=32)
    items: int = Field(1, ge=0)
    text: str = Field("", max_length=20000)
    admin_name: str = Field("", max_length=128)
    sent_at: datetime
    answered_at: datetime | None = None


class BotSyncRequest(_BotPayload):
    users: list[BotUserIn] = Field(default_factory=list, max_length=SYNC_BATCH_LIMIT)
    messages: list[BotMessageIn] = Field(
        default_factory=list, max_length=SYNC_BATCH_LIMIT
    )


class BotSyncResult(Base):
    users: int
    messages: int
    # Useri hali sync bo'lmagan xabarlar (keyingi safar qayta keladi)
    skipped_messages: int = 0


class TgUserView(Base):
    id: UUID
    telegram_id: int
    username: str
    full_name: str
    language: str
    phone: str
    reg_step: str
    is_banned: bool
    first_seen_at: datetime
    last_message_at: datetime | None = None
    messages_count: int = 0
    # Javob kutayotgan murojaatlar soni
    pending_count: int = 0


class TgUserPage(Base):
    items: list[TgUserView]
    total: int


class TgMessageView(Base):
    id: UUID
    direction: str
    status: str
    content_type: str
    items: int
    text: str
    admin_name: str
    sent_at: datetime
    answered_at: datetime | None = None


class TgMessagePage(Base):
    user: TgUserView
    items: list[TgMessageView]
    total: int

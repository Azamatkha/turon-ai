from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from src.core.schemas import Base


class EdoGuideView(Base):
    """Ro'yxatdagi bitta yo'riqnoma.

    `video_url` — qisqa muddatli imzoli havola (`?token=...`). `<video src>`
    Authorization header yubora olmaydi, shuning uchun huquq token orqali
    tekshiriladi. Havola eskirsa, ro'yxatni qayta so'rash kifoya.
    """

    id: UUID
    title: str
    size_bytes: int
    video_url: str
    created_at: datetime


class UpdateEdoGuideModel(Base):
    title: str = Field(min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Sarlavha bo'sh bo'lmasligi kerak")
        return value


class GuideUploadStartView(Base):
    """Bo'laklab yuklash boshlandi. Frontend faylni `chunk_size` dan
    oshmaydigan bo'laklarga bo'lib yuboradi."""

    upload_id: UUID
    chunk_size: int
    max_bytes: int


class GuideUploadChunkView(Base):
    # Serverda shu paytgacha yig'ilgan bayt — keyingi bo'lakning offset'i
    received: int


class CreateEdoGuideModel(Base):
    upload_id: UUID
    title: str = Field(min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Sarlavha bo'sh bo'lmasligi kerak")
        return value

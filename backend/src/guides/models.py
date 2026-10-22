from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base import Base
from src.core.database.mixins import TimestampMixin, UUIDIDMixin


class EdoGuide(Base, UUIDIDMixin, TimestampMixin):
    """EDO yo'riqnomasi — EDO'da qanday ariza yozishni ko'rsatuvchi video.

    Video fayl MEDIA_ROOT (Docker volume) ichida, bazada faqat nisbiy yo'l.
    """

    __tablename__ = "edo_guides"

    title: Mapped[str] = mapped_column(String(200))
    # MEDIA_ROOT'ga nisbatan yo'l, masalan "edo_guides/2026/10/<uuid>.mp4"
    video_path: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    # Yuklagan admin; u o'chirilsa yo'riqnoma qoladi
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

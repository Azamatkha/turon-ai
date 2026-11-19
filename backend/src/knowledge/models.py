from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base import Base
from src.core.database.mixins import TimestampMixin


class KbCategory(Base, TimestampMixin):
    """Bilim bazasi turkumi — ADMIN o'zi yaratadi va hujjatlarga o'zi qo'yadi.

    Ilgari turkum avtomatik (havola/sarlavha/matndan) taxmin qilinardi va ko'p
    adashardi. Endi avtomatik taxmin yo'q: hujjatning turkumi faqat admin
    tanlagani (Qdrant payload'idagi `category` = shu jadvaldagi `key`).
    """

    __tablename__ = "kb_categories"

    # Payload'da saqlanadigan kalit. Eski 6 ta turkum o'z kalitini saqlaydi
    # ("credit", "deposit", ...) — avval qo'lda qo'yilganlar o'zgarishsiz
    # ishlayveradi. Yangi turkumlarga tasodifiy kalit beriladi.
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    # Vergul bilan ajratilgan kalit so'zlar: savolda shulardan biri bo'lsa
    # bot shu turkum ro'yxatini beradi ("qanday kreditlar bor").
    keywords: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

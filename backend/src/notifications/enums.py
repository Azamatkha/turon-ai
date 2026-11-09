from enum import StrEnum


class NotificationType(StrEnum):
    """Bildirishnoma turi.

    Matn bazada saqlanmaydi — frontend shu tur va `params` asosida xabarni
    foydalanuvchi tiliga (uz / uz_cyrl / ru) o'giradi.
    """

    # Bilimlar bazasiga yangi hujjat qo'shildi yoki yangilandi
    KNOWLEDGE_UPDATED = "knowledge_updated"
    # Kunlik vazifa valyuta kurslarini yangiladi
    RATES_UPDATED = "rates_updated"
    # Foydalanuvchi yangi murojaat (muammo/taklif) yubordi — adminlarga
    REPORT_NEW = "report_new"
    # Bilim bazasi hujjatining muddati 7 kundan keyin tugaydi — adminlarga
    KNOWLEDGE_EXPIRING = "knowledge_expiring"
    # Hujjat muddati tugadi (kecha oxirgi kuni edi) — adminlarga
    KNOWLEDGE_EXPIRED = "knowledge_expired"
    # Avtomatik qayta scraping: ba'zi sahifalar ochilmadi — adminlarga
    KNOWLEDGE_SOURCE_FAILED = "knowledge_source_failed"
    # Xavfli so'rov yoki so'kinish aniqlandi — adminlarga (chat/usecases.py)
    SAFETY_FLAGGED = "safety_flagged"

    @classmethod
    def values(cls) -> set[str]:
        return {item.value for item in cls.__members__.values()}

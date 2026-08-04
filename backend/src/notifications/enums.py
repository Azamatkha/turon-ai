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

    @classmethod
    def values(cls) -> set[str]:
        return {item.value for item in cls.__members__.values()}

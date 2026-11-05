from enum import StrEnum


class UserRole(StrEnum):
    # Hamma narsa, jumladan rollarni almashtirish va bilim bazasi
    SUPER_ADMIN = "super_admin"
    # Boshqaruv paneli, foydalanuvchilar va murojaatlarni faqat KO'RADI
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"

    @classmethod
    def values(cls) -> set[str]:
        return {item.value for item in cls.__members__.values()}


# Admin paneliga kira oladigan rollar (bildirishnomalar ham shularga boradi)
ADMIN_PANEL_ROLES: tuple[UserRole, ...] = (UserRole.SUPER_ADMIN, UserRole.ADMIN)

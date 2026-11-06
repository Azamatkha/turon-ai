from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"

    @classmethod
    def values(cls) -> set[str]:
        return {item.value for item in cls.__members__.values()}

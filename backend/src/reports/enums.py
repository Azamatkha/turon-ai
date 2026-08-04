from enum import StrEnum


class ReportKind(StrEnum):
    """Murojaat turi — foydalanuvchi formada tanlaydi."""

    PROBLEM = "problem"
    SUGGESTION = "suggestion"

    @classmethod
    def values(cls) -> set[str]:
        return {item.value for item in cls.__members__.values()}


class ReportStatus(StrEnum):
    """Murojaat holati — admin panelda boshqariladi."""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"

    @classmethod
    def values(cls) -> set[str]:
        return {item.value for item in cls.__members__.values()}

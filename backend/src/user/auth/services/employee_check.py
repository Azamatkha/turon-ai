"""Xodimlar bazasi tekshiruvi — VAQTINCHALIK MOCK.

Xodimlar API'si hali tayyor emas. Hozircha har qanday PINFL xodim deb
hisoblanadi va quyidagi standart qiymatlar qaytadi. API ulanganda faqat
`check_employee` ichi almashtiriladi: xodim bo'lmasa `None` qaytarsin.
"""

from dataclasses import dataclass

from loggers import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class EmployeeInfo:
    position: str
    department: str
    branch: str


MOCK_EMPLOYEE = EmployeeInfo(
    position="Mutahasis",
    department="Boshqa",
    branch="Toshkent bxm",
)


async def check_employee(pnfl: str) -> EmployeeInfo | None:
    """PINFL bo'yicha xodimni topadi. Xodim bo'lmasa `None`."""
    logger.warning("[EmployeeCheck] MOCK — PINFL tekshirilmadi, standart qiymat berildi.")
    return MOCK_EMPLOYEE

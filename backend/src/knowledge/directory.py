"""Chat-bot uchun xodimlar MA'LUMOTNOMASI (users jadvali) bo'yicha qidiruv.

Xodimlar o'z kontaktini (ichki IP raqam) o'zi kiritadi, admin esa ularga
kalit so'z qo'yadi ("edo", "ip telefoniya"). Bu ma'lumot vektor bazadagi
yuklangan xodimlar ro'yxatidan YANGIROQ — shuning uchun bot avval shu yerga
qaraydi, topilmasa vektor bazaga o'tadi.

Javobda faqat ma'lumotnoma maydonlari: F.I.Sh., bo'lim, lavozim, IP. Telefon
QO'SHILMAYDI — ma'lumotnoma (DirectoryEntryModel) ham uni ochmaydi.

Oqim (SSE) yo'lida FastAPI dependency sessiyasi javob tugashidan oldin
yopilishi mumkin, shuning uchun har so'rov o'zining qisqa sessiyasini ochadi.
"""

from typing import Any

from loggers import get_logger
from src.core.database.session import async_session
from src.user.models import User
from src.user.repositories import UserRepository

logger = get_logger(__name__)


def _to_record(u: User) -> dict[str, Any]:
    """Users qatorini xodim yozuviga (_format_employee_answer formati) aylantiradi."""
    fish = " ".join(p for p in (u.last_name, u.first_name, u.patronym) if p)
    return {
        "fish": fish,
        "department": u.department or "",
        "division": "",
        "position": u.position or "",
        "ip": u.ip_number or "",
        "phone": "",
    }


async def users_by_ip(ip_numbers: set[str]) -> list[dict[str, Any]]:
    """Ichki IP raqami mos xodimlar. Xato bo'lsa — bo'sh (vektor bazaga o'tiladi)."""
    if not ip_numbers:
        return []
    try:
        async with async_session() as session:
            users = await UserRepository().directory_by_ip(session, ip_numbers)
    except Exception:  # noqa: BLE001 — DB yiqilsa bot baribir ishlashi kerak
        logger.exception("Ma'lumotnomadan IP bo'yicha qidiruv xatosi")
        return []
    return [_to_record(u) for u in users]


async def users_with_keywords() -> list[tuple[list[str], dict[str, Any]]]:
    """Kalit so'zli xodimlar: [(kalit so'zlar, yozuv), ...]."""
    try:
        async with async_session() as session:
            users = await UserRepository().directory_with_keywords(session)
    except Exception:  # noqa: BLE001
        logger.exception("Ma'lumotnomadan kalit so'z bo'yicha qidiruv xatosi")
        return []
    return [(list(u.keywords or []), _to_record(u)) for u in users]

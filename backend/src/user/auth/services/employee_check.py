"""Xodimlar bazasi (EDO) tekshiruvi — PINFL bo'yicha.

So'rov:  POST {EMPLOYEE_API_URL}  {"pin": "<PINFL>"}
Javob:   {"success": true, "data": {"depart": "...", "positon": "..."}}
         {"success": false, ...} — xodim emas.

Tarmoq xatosi / 5xx / tushunarsiz javob `InfrastructureException` (500) bo'ladi:
mobil bunda "qayta urinish" kartasini ko'rsatadi — foydalanuvchi "xodim emas"
deb noto'g'ri rad etilmaydi.
"""

from dataclasses import dataclass
from typing import Any

import httpx

from loggers import get_logger
from src.core.errors.exceptions import InfrastructureException
from src.main.config import config
from src.user.auth.schemas import DEFAULT_DEPARTMENT

logger = get_logger(__name__)


@dataclass(frozen=True)
class EmployeeInfo:
    position: str | None
    department: str


def _clean(value: Any, max_length: int) -> str | None:
    if value is None:
        return None
    # API matnida qo'sh bo'shliqlar uchraydi ("departamenti  (IT ...)")
    text = " ".join(str(value).split())
    return text[:max_length] or None


async def check_employee(http: httpx.AsyncClient, pnfl: str) -> EmployeeInfo | None:
    """PINFL bo'yicha xodimni topadi. Xodim bo'lmasa `None`."""
    try:
        resp = await http.post(
            config.employee_api.EMPLOYEE_API_URL,
            json={"pin": pnfl},
            timeout=config.employee_api.EMPLOYEE_API_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        logger.error("[EmployeeCheck] Xodimlar API'siga ulanib bo'lmadi: %r", exc)
        raise InfrastructureException("Xodimlar bazasi javob bermadi") from exc

    try:
        payload = resp.json()
    except ValueError:
        payload = None

    if not isinstance(payload, dict) or "success" not in payload:
        logger.error(
            "[EmployeeCheck] Kutilmagan javob: status=%s body=%r",
            resp.status_code,
            resp.text[:300],
        )
        raise InfrastructureException("Xodimlar bazasi javob bermadi")

    if payload.get("success") is not True:
        logger.info("[EmployeeCheck] Xodim topilmadi (status=%s).", resp.status_code)
        return None

    data = payload.get("data") or {}
    return EmployeeInfo(
        # API kalitida xato bor ("positon") — to'g'rilanib qolsa ham ishlasin
        position=_clean(data.get("positon") or data.get("position"), 150),
        department=_clean(data.get("depart"), 100) or DEFAULT_DEPARTMENT,
    )

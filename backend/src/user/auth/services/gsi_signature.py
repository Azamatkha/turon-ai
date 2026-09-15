"""GSI Face-ID natijasi (`signature`) ni o'qish.

`signature` — GSI HS256 bilan imzolagan JWT. Uning claim'lari:
- `body`  — tasdiqlangan shaxs ma'lumoti, JSON SATR ko'rinishida (ikkinchi
            marta parse qilinadi);
- `token` — biz register'da bergan accessToken (GSI o'zgartirmay qaytaradi);
- `requestId`, `score`, `photoHash`/`captureHash`/`videoHash` va metadata.

Tartib hujjatdagidek: imzo -> bizning token -> body.
"""

from dataclasses import dataclass
from datetime import date, datetime
import json
import re
from typing import Any
from uuid import UUID

import jwt

from loggers import get_logger
from src.core.errors.exceptions import InstanceProcessingException
from src.main.config import config

logger = get_logger(__name__)

INVALID_SIGNATURE_MESSAGE = "Face-ID natijasi yaroqsiz"

# Telefon va server soati orasidagi farq uchun zaxira (soniya)
CLOCK_LEEWAY_SECONDS = 60


@dataclass(frozen=True)
class GsiPerson:
    """`body` dan ajratib olingan shaxs ma'lumoti (users jadvali ustunlariga mos)."""

    pnfl: str
    first_name: str
    last_name: str
    patronym: str | None
    doc_seria: str | None
    doc_number: str | None
    birth_date: date | None


def decode_signature(signature: str) -> dict[str, Any]:
    """1-qadam: imzoni tekshirib, claim'larni qaytaradi.

    `GSI_HMAC_KEY` hali yo'q bo'lsa — faqat decode (test rejimi).
    """
    key = config.jwt.GSI_HMAC_KEY
    try:
        if key:
            return jwt.decode(
                signature,
                key,
                algorithms=["HS256"],
                leeway=CLOCK_LEEWAY_SECONDS,
                options={"verify_aud": False},
            )
        logger.warning(
            "[FaceID] GSI_HMAC_KEY yo'q — imzo TEKSHIRILMADI (faqat test uchun)."
        )
        return jwt.decode(
            signature,
            options={"verify_signature": False, "verify_exp": False},
        )
    except jwt.PyJWTError as exc:
        logger.info("[FaceID] Imzo rad etildi: %s", exc)
        raise InstanceProcessingException(INVALID_SIGNATURE_MESSAGE) from exc


def user_id_from_token(token: Any) -> UUID:
    """2-qadam: `claims["token"]` — bizning accessToken. Undan user aniqlanadi.

    `exp` tekshirilmaydi: skanerlash token muddatidan cho'zilishi mumkin, imzo
    esa baribir GSI tomonidan yangi qo'yilgan.
    """
    if not isinstance(token, str) or not token:
        raise InstanceProcessingException(INVALID_SIGNATURE_MESSAGE)
    try:
        payload = jwt.decode(
            token,
            config.jwt.JWT_USER_SECRET_KEY,
            algorithms=[config.jwt.ALGORITHM],
            options={"verify_exp": False},
        )
        if payload.get("mode") != "access_token":
            raise ValueError("token turi access_token emas")
        return UUID(str(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        logger.info("[FaceID] Ichki token rad etildi: %s", exc)
        raise InstanceProcessingException(INVALID_SIGNATURE_MESSAGE) from exc


# ----- body ----- #
def _find(data: Any, *keys: str) -> Any:
    """Kalitni avval yuqori darajada, keyin ichma-ich obyektlarda qidiradi.

    GSI javobining aniq tuzilishi (maydonlar ichki obyektdami) hali
    tasdiqlanmagan — shu sabab chuqur qidiramiz.
    """
    if isinstance(data, dict):
        for key in keys:
            value = data.get(key)
            if value not in (None, ""):
                return value
        for value in data.values():
            found = _find(value, *keys)
            if found not in (None, ""):
                return found
    elif isinstance(data, list):
        for item in data:
            found = _find(item, *keys)
            if found not in (None, ""):
                return found
    return None


def _text(value: Any, max_length: int) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text[:max_length] or None


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    raw = str(value).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y", "%Y.%m.%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    logger.warning("[FaceID] Tug'ilgan sana formati tanilmadi: %r", value)
    return None


def _split_document(value: Any) -> tuple[str | None, str | None]:
    """`current_document` -> (seriya, raqam). "AA1234567" -> ("AA", "1234567"),
    faqat raqam bo'lsa ("763412340") -> (None, "763412340")."""
    if not value:
        return None, None
    raw = re.sub(r"\s+", "", str(value)).upper()
    match = re.fullmatch(r"([A-Z]{1,4})(\d+)", raw)
    if match:
        return match.group(1), match.group(2)
    return None, raw[:20]


def extract_person(body: Any) -> GsiPerson:
    """4-qadam: `body` dan shaxsni o'qiydi. PNFL bo'lmasa — rad etiladi."""
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError as exc:
            raise InstanceProcessingException(INVALID_SIGNATURE_MESSAGE) from exc
    if not isinstance(body, dict):
        raise InstanceProcessingException(INVALID_SIGNATURE_MESSAGE)

    pnfl = re.sub(r"\D", "", str(_find(body, "pin", "doc_pinfl", "pinfl", "pnfl") or ""))
    if len(pnfl) != 14:
        logger.info("[FaceID] body'da yaroqli PINFL yo'q.")
        raise InstanceProcessingException("Face-ID natijasida PINFL topilmadi")

    doc_seria = _text(_find(body, "doc_seria", "document_seria"), 10)
    doc_number = _text(_find(body, "doc_number", "document_number"), 20)
    if not doc_number:
        doc_seria, doc_number = _split_document(_find(body, "current_document"))

    return GsiPerson(
        pnfl=pnfl,
        first_name=_text(_find(body, "namelat", "name_lat", "first_name", "namecyr"), 50)
        or "",
        last_name=_text(
            _find(body, "surnamelat", "surname_lat", "last_name", "surnamecyr"), 50
        )
        or "",
        patronym=_text(
            _find(body, "patronymlat", "patronym_lat", "patronym", "patronymcyr"), 50
        ),
        doc_seria=doc_seria.upper() if doc_seria else None,
        doc_number=doc_number,
        birth_date=_parse_date(_find(body, "birth_date", "birthdate", "date_birth")),
    )

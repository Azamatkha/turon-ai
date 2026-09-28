"""Mobil ilova uchun client PKCS#12 (.p12) sertifikat.

Bank CA'si (`Turonbank Mobile Client CA`) bitta client sertifikat berdi
(`faceids-mobile-01`) — u `certs/` papkasida shifrlangan holda turadi, paroli
esa faqat .env da (`CERT_P12_PASSWORD`). CA'ning maxfiy kaliti bizda YO'Q,
shuning uchun har userga alohida sertifikat imzolanmaydi: hammaga shu bitta
p12 va uning paroli qaytariladi (mobil uni ochishi uchun parol kerak).

Fayl yo'q bo'lsa, faqat DEBUG rejimda eski mock (self-signed) ishlatiladi —
prodda mobilga soxta sertifikat jimgina ketib qolmasligi uchun xato beriladi.
"""

import base64
from functools import lru_cache
from pathlib import Path

from cryptography.hazmat.primitives.serialization import pkcs12

from loggers import get_logger
from src.main.config import config
from src.user.auth.services.mock_p12 import generate_mock_p12

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _load_client_p12() -> tuple[str, str]:
    """Faylni o'qib, parol bilan ochib tekshiradi; (p12_base64, parol) qaytaradi.

    Natija keshlanadi — fayl va parol faqat ilova qayta ishga tushganda
    o'zgaradi.
    """
    path = Path(config.certificate.CERT_P12_PATH)
    password = config.certificate.CERT_P12_PASSWORD
    if not password:
        raise RuntimeError("CERT_P12_PASSWORD .env da berilmagan")

    p12_bytes = path.read_bytes()
    # Parol xato yoki fayl buzilgan bo'lsa shu yerda ValueError chiqadi —
    # mobil ochib bo'lmaydigan p12 olishidan ko'ra, xatoni serverda ko'rgan yaxshi
    key, cert, _ = pkcs12.load_key_and_certificates(p12_bytes, password.encode())
    if key is None or cert is None:
        raise RuntimeError(f"{path} ichida client sertifikat yoki kalit yo'q")

    logger.info(
        "Client p12 yuklandi: %s (amal qiladi: %s gacha)",
        cert.subject.rfc4514_string(),
        cert.not_valid_after_utc.date(),
    )
    return base64.b64encode(p12_bytes).decode("ascii"), password


def get_client_p12(common_name: str) -> tuple[str, str]:
    """(p12_base64, p12_password) qaytaradi.

    Mock fallback RSA kalit yaratgani uchun CPU'ni band qiladi — async
    koddan `asyncio.to_thread` orqali chaqirilsin.
    """
    if not Path(config.certificate.CERT_P12_PATH).exists() and config.app.DEBUG:
        logger.warning(
            "%s topilmadi — DEBUG rejim, mock p12 ishlatiladi",
            config.certificate.CERT_P12_PATH,
        )
        return generate_mock_p12(common_name)
    return _load_client_p12()

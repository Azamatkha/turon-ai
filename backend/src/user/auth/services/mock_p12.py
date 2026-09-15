"""VAQTINCHALIK mock PKCS#12 (.p12) generatori.

Haqiqiy sertifikat beruvchi xizmat (CA) hali ulanmagan. Mobil ilova esa
register javobida p12 + parolni kutadi. Shu sabab har bir register uchun
o'z-o'zidan imzolangan (self-signed) sertifikat va kalit yaratiladi —
tasodifiy baytlar emas, HAQIQIY p12: mobil uni ochib, import qilib sinay oladi.

Haqiqiy CA ulanganda shu modul almashtiriladi, javob formati o'zgarmaydi.
"""

import base64
import secrets
from datetime import UTC, datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

# Mock sertifikat amal qilish muddati
MOCK_CERT_VALID_DAYS = 365


def generate_mock_p12(common_name: str) -> tuple[str, str]:
    """(p12_base64, p12_password) qaytaradi.

    RSA kalit yaratish CPU'ni ~50-100 ms band qiladi — async koddan
    `asyncio.to_thread` orqali chaqirilsin.
    """
    password = secrets.token_urlsafe(16)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Turonbank (mock)"),
        ]
    )
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=MOCK_CERT_VALID_DAYS))
        .sign(key, hashes.SHA256())
    )

    p12_bytes = pkcs12.serialize_key_and_certificates(
        name=common_name.encode(),
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(password.encode()),
    )
    return base64.b64encode(p12_bytes).decode("ascii"), password

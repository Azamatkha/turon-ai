"""Mobil ilova uchun client PKCS#12 (.p12) sertifikat.

mTLS proxy (9443) ishonadigan CA'ning sertifikati va maxfiy kaliti backend'da
(`certs/mobile-ca.crt`, `certs/mobile-ca.key`). Har register va tasdiqlanmagan
login'da userga ALOHIDA, qisqa muddatli (`CLIENT_CERT_TTL_MINUTES`, ≤ 20 daq —
GSI hujjati 6.2) sertifikat imzolanadi va tasodifiy parol bilan p12'ga
o'raladi. Hech qayerda saqlanmaydi: javobga qo'yiladi va unutiladi.

CA fayllari yo'q bo'lsa faqat DEBUG rejimda mock (self-signed) ishlatiladi —
prodda mobilga soxta sertifikat jimgina ketib qolmasligi uchun xato beriladi.
"""

import base64
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
import secrets

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.types import CertificateIssuerPrivateKeyTypes
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from loggers import get_logger
from src.main.config import config
from src.user.auth.services.mock_p12 import generate_mock_p12

logger = get_logger(__name__)

# Backend va proxy serverlari soati orasidagi farq uchun: sertifikat shuncha
# oldin "boshlanadi", umumiy muddat esa baribir TTL dan oshmaydi
CLOCK_SKEW = timedelta(minutes=1)

CLIENT_ORGANIZATION = "Turonbank"
CLIENT_COUNTRY = "UZ"


@lru_cache(maxsize=1)
def _load_ca() -> tuple[x509.Certificate, CertificateIssuerPrivateKeyTypes]:
    """CA sertifikat va kalitini o'qiydi va tekshiradi. Natija keshlanadi —
    fayllar faqat ilova qayta ishga tushganda o'zgaradi."""
    cert_path = Path(config.certificate.CLIENT_CA_CERT_PATH)
    key_path = Path(config.certificate.CLIENT_CA_KEY_PATH)
    password = config.certificate.CLIENT_CA_KEY_PASSWORD

    ca_cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
    key_bytes = key_path.read_bytes()
    try:
        ca_key = serialization.load_pem_private_key(
            key_bytes, password=password.encode() if password else None
        )
    except TypeError:
        # Kalit shifrlanmagan, .env da esa parol yozilgan (yoki aksincha)
        if not password:
            raise RuntimeError(f"{key_path} shifrlangan — CLIENT_CA_KEY_PASSWORD kerak")
        logger.warning(
            "%s shifrlanmagan — CLIENT_CA_KEY_PASSWORD e'tiborsiz qoldirildi", key_path
        )
        ca_key = serialization.load_pem_private_key(key_bytes, password=None)

    try:
        is_ca = ca_cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca
    except x509.ExtensionNotFound:
        is_ca = False
    if not is_ca:
        raise RuntimeError(f"{cert_path} CA sertifikat emas (CA:TRUE yo'q)")

    public_format = (serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    if ca_key.public_key().public_bytes(*public_format) != ca_cert.public_key().public_bytes(
        *public_format
    ):
        raise RuntimeError(f"{key_path} kaliti {cert_path} sertifikatiga mos emas")

    logger.info(
        "Client CA yuklandi: %s (amal qiladi: %s gacha)",
        ca_cert.subject.rfc4514_string(),
        ca_cert.not_valid_after_utc.date(),
    )
    return ca_cert, ca_key  # type: ignore[return-value]


def _issue_p12(common_name: str) -> tuple[str, str]:
    ca_cert, ca_key = _load_ca()
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    not_before = datetime.now(UTC) - CLOCK_SKEW
    not_after = not_before + timedelta(minutes=config.certificate.CLIENT_CERT_TTL_MINUTES)

    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, CLIENT_ORGANIZATION),
            x509.NameAttribute(NameOID.COUNTRY_NAME, CLIENT_COUNTRY),
        ]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_cert.public_key()),  # type: ignore[arg-type]
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )

    password = secrets.token_urlsafe(16)
    p12_bytes = pkcs12.serialize_key_and_certificates(
        name=common_name.encode(),
        key=key,
        cert=cert,
        cas=[ca_cert],
        encryption_algorithm=serialization.BestAvailableEncryption(password.encode()),
    )
    logger.info(
        "[FaceID] Client sertifikat berildi: CN=%s, serial=%x, %s gacha",
        common_name,
        cert.serial_number,
        not_after.isoformat(timespec="seconds"),
    )
    return base64.b64encode(p12_bytes).decode("ascii"), password


def get_client_p12(common_name: str) -> tuple[str, str]:
    """(p12_base64, p12_password) qaytaradi — har chaqiruvda yangi sertifikat.

    RSA kalit yaratish CPU'ni band qiladi — async koddan `asyncio.to_thread`
    orqali chaqirilsin.
    """
    ca_files_exist = (
        Path(config.certificate.CLIENT_CA_CERT_PATH).exists()
        and Path(config.certificate.CLIENT_CA_KEY_PATH).exists()
    )
    if not ca_files_exist:
        if config.app.DEBUG:
            logger.warning("Client CA fayllari topilmadi — DEBUG rejim, mock p12 ishlatiladi")
            return generate_mock_p12(common_name)
        raise RuntimeError(
            "Client CA fayllari topilmadi: "
            f"{config.certificate.CLIENT_CA_CERT_PATH}, {config.certificate.CLIENT_CA_KEY_PATH}"
        )
    return _issue_p12(common_name)

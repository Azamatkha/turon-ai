import base64
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
import pytest

import src.user.auth.services.client_p12 as client_p12


def _write_ca(tmp_path: Path, *, is_ca: bool = True) -> tuple[x509.Certificate, Path, Path]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test Mobile CA")])
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=is_ca, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    cert_path = tmp_path / "mobile-ca.crt"
    key_path = tmp_path / "mobile-ca.key"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return cert, cert_path, key_path


@pytest.fixture
def ca(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> x509.Certificate:
    cert, cert_path, key_path = _write_ca(tmp_path)
    monkeypatch.setattr(client_p12.config.certificate, "CLIENT_CA_CERT_PATH", str(cert_path))
    monkeypatch.setattr(client_p12.config.certificate, "CLIENT_CA_KEY_PATH", str(key_path))
    monkeypatch.setattr(client_p12.config.certificate, "CLIENT_CA_KEY_PASSWORD", "")
    monkeypatch.setattr(client_p12.config.certificate, "CLIENT_CERT_TTL_MINUTES", 20)
    client_p12._load_ca.cache_clear()
    yield cert
    client_p12._load_ca.cache_clear()


def _open(p12_base64: str, password: str):  # type: ignore[no-untyped-def]
    return pkcs12.load_key_and_certificates(base64.b64decode(p12_base64), password.encode())


def test_issued_p12_is_short_lived_client_cert_signed_by_ca(ca: x509.Certificate) -> None:
    """
    Given: proxy ishonadigan CA.
    When: user uchun p12 so'raladi.
    Then: CA imzolagan, ≤ 20 daqiqalik, faqat client auth uchun sertifikat.
    """
    p12_base64, password = client_p12.get_client_p12("azamat")
    key, cert, chain = _open(p12_base64, password)

    assert key is not None and cert is not None
    # Proxy'da ishlaydigan umumiy turon.p12 qolipi: C, O, OU=Mobile, CN tartibida
    assert cert.subject.rfc4514_string() == "CN=azamat,OU=Mobile,O=Turonbank,C=UZ"
    key_usage = cert.extensions.get_extension_for_class(x509.KeyUsage).value
    assert key_usage.digital_signature and not key_usage.key_encipherment
    assert cert.issuer == ca.subject
    assert cert.not_valid_after_utc - cert.not_valid_before_utc <= timedelta(minutes=20)
    assert cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca is False
    assert (
        ExtendedKeyUsageOID.CLIENT_AUTH
        in cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
    )
    # Imzo haqiqatan CA kaliti bilan qo'yilgan (xato bo'lsa exception)
    ca.public_key().verify(  # type: ignore[call-arg]
        cert.signature,
        cert.tbs_certificate_bytes,
        padding.PKCS1v15(),
        cert.signature_hash_algorithm,
    )
    assert [c.subject for c in chain] == [ca.subject]
    # Mobil kalitni shu alias bo'yicha topadi
    loaded = pkcs12.load_pkcs12(base64.b64decode(p12_base64), password.encode())
    assert loaded.cert is not None and loaded.cert.friendly_name == b"Turonbank FaceIDS Mobile"


def test_each_call_issues_new_cert_key_and_password(ca: x509.Certificate) -> None:
    first_b64, first_pwd = client_p12.get_client_p12("azamat")
    second_b64, second_pwd = client_p12.get_client_p12("azamat")
    first_key, first_cert, _ = _open(first_b64, first_pwd)
    second_key, second_cert, _ = _open(second_b64, second_pwd)

    assert first_pwd != second_pwd
    assert first_cert.serial_number != second_cert.serial_number  # type: ignore[union-attr]
    assert first_key.public_key().public_numbers() != second_key.public_key().public_numbers()  # type: ignore[union-attr]


def test_non_ca_certificate_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, cert_path, key_path = _write_ca(tmp_path, is_ca=False)
    monkeypatch.setattr(client_p12.config.certificate, "CLIENT_CA_CERT_PATH", str(cert_path))
    monkeypatch.setattr(client_p12.config.certificate, "CLIENT_CA_KEY_PATH", str(key_path))
    client_p12._load_ca.cache_clear()

    with pytest.raises(RuntimeError, match="CA sertifikat emas"):
        client_p12.get_client_p12("azamat")
    client_p12._load_ca.cache_clear()


def test_key_not_matching_certificate_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    _, cert_path, _ = _write_ca(tmp_path / "a")
    _, _, other_key_path = _write_ca(tmp_path / "b")
    monkeypatch.setattr(client_p12.config.certificate, "CLIENT_CA_CERT_PATH", str(cert_path))
    monkeypatch.setattr(client_p12.config.certificate, "CLIENT_CA_KEY_PATH", str(other_key_path))
    client_p12._load_ca.cache_clear()

    with pytest.raises(RuntimeError, match="mos emas"):
        client_p12.get_client_p12("azamat")
    client_p12._load_ca.cache_clear()


def test_missing_ca_in_production_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        client_p12.config.certificate, "CLIENT_CA_CERT_PATH", str(tmp_path / "yoq.crt")
    )
    monkeypatch.setattr(
        client_p12.config.certificate, "CLIENT_CA_KEY_PATH", str(tmp_path / "yoq.key")
    )
    monkeypatch.setattr(client_p12.config.app, "DEBUG", False)

    with pytest.raises(RuntimeError, match="topilmadi"):
        client_p12.get_client_p12("azamat")

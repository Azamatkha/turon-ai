from pydantic import ValidationError
import pytest

from src.user.auth.schemas import UserNewPassword

# Parol o'zgartirishda joriy parol ham majburiy (o'g'irlangan tokendan himoya).
# Bu testlar YANGI parol validatsiyasini tekshiradi, shuning uchun joriy parol
# har joyda bir xil o'rinbosar qiymat.
CURRENT = "oldpassword"


def test_user_new_password_allows_printable_ascii_symbols_outside_old_whitelist() -> (
    None
):
    password = "Strong1~ "

    model = UserNewPassword(current_password=CURRENT, password=password)

    assert model.password == password


def test_user_new_password_allows_maximum_length_boundary() -> None:
    password = "Aa1!" + ("x" * 124)

    model = UserNewPassword(current_password=CURRENT, password=password)

    assert len(model.password) == 128


def test_user_new_password_rejects_password_longer_than_128_characters() -> None:
    password = "Aa1!" + ("x" * 125)

    with pytest.raises(ValidationError) as exc_info:
        UserNewPassword(current_password=CURRENT, password=password)

    # Xabar `src/core/validations.py` dagi PASSWORD_MIN/MAX_LENGTH dan hosil
    # bo'ladi. Murakkablik talabi (katta harf, raqam, belgi) ATAYLAB olib
    # tashlangan, shuning uchun xabar ham faqat uzunlik haqida.
    error_message = exc_info.value.errors()[0]["msg"]
    assert error_message == "Value error, Password must be 4-128 characters long."


def test_user_new_password_rejects_non_ascii_characters() -> None:
    with pytest.raises(ValidationError):
        UserNewPassword(current_password=CURRENT, password="Strong1!пароль")


def test_user_new_password_requires_current_password() -> None:
    """Joriy parolsiz so'rov umuman qabul qilinmaydi."""
    with pytest.raises(ValidationError):
        UserNewPassword(password="StrongPass1!")  # type: ignore[call-arg]

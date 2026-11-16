"""Rol katta-kichik harfdan qat'i nazar qabul qilinadi (mobil "ADMIN" yuboradi)."""

from pydantic import ValidationError
import pytest

from src.user.enums import UserRole
from src.user.schemas import AdminUpdateUserModel


@pytest.mark.parametrize("raw", ["ADMIN", "admin", "Admin", " admin "])
def test_role_any_case(raw: str) -> None:
    assert AdminUpdateUserModel(role=raw).role == UserRole.ADMIN


def test_moderator_upper() -> None:
    assert AdminUpdateUserModel(role="MODERATOR").role == UserRole.MODERATOR


def test_unknown_role_still_rejected() -> None:
    with pytest.raises(ValidationError):
        AdminUpdateUserModel(role="SUPERADMIN")


def test_role_optional() -> None:
    assert AdminUpdateUserModel().role is None

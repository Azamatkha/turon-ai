from uuid import UUID

import pytest

from src.user.auth.turon_id.domain import (
    PLACEHOLDER_EMAIL_DOMAIN,
    chat_roles,
    fallback_username,
    placeholder_email,
)
from src.user.enums import UserRole

SUB = UUID("7f0c2a52-6d3e-4f7a-9a56-0d4d1c1c3b11")


@pytest.mark.parametrize(
    ("claims", "expected"),
    [
        ({"plt": {"chat": ["user", "admin"]}}, (UserRole.ADMIN, UserRole.USER)),
        ({"plt": {"chat": ["moderator", "unknown"]}}, (UserRole.MODERATOR,)),
        ({"plt": {"biznes": ["admin"]}}, ()),  # other platforms do not count
        ({"plt": {"chat": "admin"}}, ()),  # malformed
        ({}, ()),
    ],
)
def test_chat_roles(claims: dict, expected: tuple[UserRole, ...]) -> None:
    assert chat_roles(claims) == expected


def test_placeholders_are_stable_and_valid_looking() -> None:
    assert placeholder_email(SUB) == f"{SUB}@{PLACEHOLDER_EMAIL_DOMAIN}"
    assert fallback_username(SUB) == "tid_7f0c2a526d3e"


def test_placeholder_email_passes_the_chat_email_validator() -> None:
    from pydantic import TypeAdapter
    from pydantic import EmailStr

    assert TypeAdapter(EmailStr).validate_python(placeholder_email(SUB))

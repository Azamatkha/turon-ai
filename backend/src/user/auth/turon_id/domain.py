"""Turon ID sign-in: pure rules (no HTTP, no database)."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final
from uuid import UUID

from src.user.enums import UserRole

PLATFORM_CODE: Final = "chat"
# Strongest first; Turon ID role codes on the `chat` platform equal ours.
ROLE_PRECEDENCE: Final = (UserRole.ADMIN, UserRole.MODERATOR, UserRole.USER)
NAME_MAX_LENGTH: Final = 50
USERNAME_MAX_LENGTH: Final = 60
# Chat requires a valid e-mail per account (EmailStr). SSO users without one get
# a placeholder in a bank subdomain without mailboxes; reserved TLDs such as
# .invalid are rejected by the e-mail validator.
PLACEHOLDER_EMAIL_DOMAIN: Final = "sso.turonbank.uz"


@dataclass(frozen=True, slots=True)
class TuronIdProfile:
    """Who signed in, from the verified access token plus Turon ID /users/me."""

    sub: UUID
    roles: tuple[UserRole, ...]
    username: str | None
    first_name: str | None
    last_name: str | None
    email: str | None
    phone_number: str | None

    @property
    def role(self) -> UserRole:
        return self.roles[0]


def chat_roles(claims: Mapping[str, Any]) -> tuple[UserRole, ...]:
    """This platform's roles from the `plt` claim, strongest first."""
    by_platform = claims.get("plt")
    codes = by_platform.get(PLATFORM_CODE) if isinstance(by_platform, Mapping) else None
    if not isinstance(codes, list):
        return ()
    known = {role for role in ROLE_PRECEDENCE if role.value in codes}
    return tuple(role for role in ROLE_PRECEDENCE if role in known)


def placeholder_email(sub: UUID) -> str:
    return f"{sub}@{PLACEHOLDER_EMAIL_DOMAIN}"


def fallback_username(sub: UUID) -> str:
    return f"tid_{sub.hex[:12]}"


def trim(value: str | None, limit: int) -> str:
    return (value or "").strip()[:limit]

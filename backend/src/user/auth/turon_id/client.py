"""Turon ID API as seen from the chat backend (infrastructure)."""

from typing import Any, Protocol
from uuid import UUID

import httpx
import jwt

from loggers import get_logger
from src.core.errors.exceptions import InfrastructureException, UnauthorizedException
from src.user.auth.turon_id.domain import TuronIdProfile, chat_roles

logger = get_logger(__name__)

_SSO_TOKEN_PATH = "/v1/users/auth/sso/token"
_PROFILE_PATH = "/v1/users/me"
_INVALID_CODE = "Turon ID sign-in failed"


class TuronIdGateway(Protocol):
    async def sign_in(self, code: str) -> TuronIdProfile: ...


class HttpTuronIdGateway:
    """
    Exchanges a one-time SSO code for a Turon ID access token (client secret),
    verifies the token locally with Turon ID's public key and reads the profile.
    """

    def __init__(
        self,
        *,
        api_url: str,
        client_id: str,
        client_secret: str,
        public_key: str,
        algorithm: str,
        timeout_seconds: float,
    ) -> None:
        self._api_url = api_url.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self._public_key = public_key.replace("\\n", "\n")
        self._algorithm = algorithm
        self._timeout = timeout_seconds

    async def sign_in(self, code: str) -> TuronIdProfile:
        # Turon ID is always inside the bank network: never via HTTP(S)_PROXY,
        # which Docker injects into containers and httpx would honour.
        async with httpx.AsyncClient(
            base_url=self._api_url, timeout=self._timeout, trust_env=False
        ) as http:
            token = await self._exchange(http, code)
            claims = self._verify(token)
            profile = await self._profile(http, token)
        roles = chat_roles(claims)
        if not roles:
            # Turon ID already refuses users without a chat role; double-check.
            raise UnauthorizedException(_INVALID_CODE)
        return TuronIdProfile(
            sub=UUID(str(claims["sub"])),
            roles=roles,
            username=profile.get("username"),
            first_name=profile.get("first_name") or claims.get("first_name"),
            last_name=profile.get("last_name") or claims.get("last_name"),
            email=profile.get("email") or claims.get("email"),
            phone_number=profile.get("phone_number") or claims.get("phone_number"),
        )

    async def _exchange(self, http: httpx.AsyncClient, code: str) -> str:
        try:
            response = await http.post(
                _SSO_TOKEN_PATH,
                json={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code": code,
                },
            )
        except httpx.HTTPError as exc:
            raise InfrastructureException("Turon ID is unavailable") from exc
        if response.status_code in (400, 401, 403, 422):
            logger.info("[TuronId] code exchange refused: %s", response.status_code)
            raise UnauthorizedException(_INVALID_CODE)
        if response.status_code != httpx.codes.OK:
            raise InfrastructureException(f"Turon ID answered {response.status_code}")
        token = response.json().get("access_token")
        if not isinstance(token, str) or not token:
            raise InfrastructureException("Turon ID returned no access token")
        return token

    def _verify(self, token: str) -> dict[str, Any]:
        try:
            claims: dict[str, Any] = jwt.decode(
                token,
                self._public_key,
                algorithms=[self._algorithm],
                options={"require": ["exp", "iat", "sub"], "verify_aud": False},
            )
        except jwt.PyJWTError as exc:
            raise UnauthorizedException(_INVALID_CODE) from exc
        if claims.get("mode") != "access_token":
            raise UnauthorizedException(_INVALID_CODE)
        return claims

    async def _profile(self, http: httpx.AsyncClient, token: str) -> dict[str, Any]:
        try:
            response = await http.get(
                _PROFILE_PATH, headers={"Authorization": f"Bearer {token}"}
            )
        except httpx.HTTPError as exc:
            raise InfrastructureException("Turon ID is unavailable") from exc
        if response.status_code != httpx.codes.OK:
            raise InfrastructureException(f"Turon ID profile: {response.status_code}")
        body = response.json()
        return body if isinstance(body, dict) else {}

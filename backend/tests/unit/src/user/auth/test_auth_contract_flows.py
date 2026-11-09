from dataclasses import dataclass

from fastapi import Request
import pytest

from src.core.errors.exceptions import UnauthorizedException
from src.core.schemas import TokenModel
from src.user.auth.dependencies import (
    get_access_by_refresh_token,
    get_current_user,
    get_current_user_allow_unverified,
)
from src.user.auth.jwt_payload_schema import JWTPayload
from src.user.auth.schemas import (
    LoginTokenModel,
    LoginUserModel,
)
from src.user.auth.usecases.get_access_by_refresh import (
    get_tokens_by_refresh_user_use_case,
)
from src.user.auth.usecases.login import get_login_user_use_case
from src.user.models import User
from tests.factories.token_factory import build_refresh_payload
from tests.factories.user_factory import build_user
from tests.helpers.limiter import noop_rate_limiter
from tests.helpers.overrides import DependencyOverrides
from tests.helpers.providers import ProvideValue


@dataclass
class TokenState:
    access_token: str | None = None
    refresh_token: str | None = None


class LoginUseCaseFake:
    def __init__(self, state: TokenState, access_token: str, refresh_token: str):
        self._state = state
        self._access_token = access_token
        self._refresh_token = refresh_token

    async def execute(self, data: LoginUserModel) -> LoginTokenModel:
        self._state.access_token = self._access_token
        self._state.refresh_token = self._refresh_token
        return LoginTokenModel(
            access_token=self._access_token,
            refresh_token=self._refresh_token,
            is_verified=True,
        )


class RefreshUseCaseFake:
    def __init__(self, state: TokenState, access_token: str, refresh_token: str):
        self._state = state
        self._access_token = access_token
        self._refresh_token = refresh_token

    async def execute(self, user: User, old_token_payload: JWTPayload) -> TokenModel:
        self._state.access_token = self._access_token
        self._state.refresh_token = self._refresh_token
        return TokenModel(
            access_token=self._access_token, refresh_token=self._refresh_token
        )


class RefreshTokenDependency:
    def __init__(self, state: TokenState, user: User, payload: JWTPayload):
        self._state = state
        self._user = user
        self._payload = payload

    async def __call__(self, request: Request) -> tuple[User, JWTPayload]:
        expected = self._build_expected(self._state.refresh_token)
        token = request.headers.get("Authorization")
        if token != expected:
            raise UnauthorizedException("Invalid refresh token")
        return self._user, self._payload

    @staticmethod
    def _build_expected(token: str | None) -> str:
        if not token:
            return ""
        return f"Bearer {token}"


class AccessTokenDependency:
    def __init__(self, state: TokenState, user: User):
        self._state = state
        self._user = user

    async def __call__(self, request: Request) -> User:
        expected = self._build_expected(self._state.access_token)
        token = request.headers.get("Authorization")
        if token != expected:
            raise UnauthorizedException("Invalid access token")
        return self._user

    @staticmethod
    def _build_expected(token: str | None) -> str:
        if not token:
            return ""
        return f"Bearer {token}"


@pytest.fixture(autouse=True)
def disable_rate_limiter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.core.limiter.depends.RateLimiter.__call__",
        noop_rate_limiter,
    )


@pytest.mark.asyncio
async def test_login_refresh_access_flow(
    async_client,
    dependency_overrides: DependencyOverrides,
) -> None:
    """
    Given: a client receives initial login tokens and later uses refreshed tokens.
    When: login, refresh, and /users/me requests are executed in sequence.
    Then: each step succeeds and /users/me is authorized by the latest access token.
    """
    state = TokenState()
    user = build_user()
    payload = build_refresh_payload(str(user.id))

    login_use_case = LoginUseCaseFake(
        state=state,
        access_token="access-1",
        refresh_token="refresh-1",
    )
    refresh_use_case = RefreshUseCaseFake(
        state=state,
        access_token="access-2",
        refresh_token="refresh-2",
    )
    refresh_dependency = RefreshTokenDependency(state, user, payload)
    access_dependency = AccessTokenDependency(state, user)

    dependency_overrides.set(get_login_user_use_case, ProvideValue(login_use_case))
    dependency_overrides.set(
        get_tokens_by_refresh_user_use_case, ProvideValue(refresh_use_case)
    )
    dependency_overrides.set(get_access_by_refresh_token, refresh_dependency)
    dependency_overrides.set(get_current_user, access_dependency)
    # /me tasdiqlanmagan userga ham ochiq — u shu dependency orqali ishlaydi
    dependency_overrides.set(get_current_user_allow_unverified, access_dependency)

    login_response = await async_client.post(
        "/v1/users/auth/login",
        json={"username": "user", "password": "StrongPass1!"},
    )

    assert login_response.status_code == 200
    # Tasdiqlangan user: tokenlar to'la, Face-ID maydonlari (token, p12) bo'sh
    assert login_response.json() == {
        "access_token": "access-1",
        "refresh_token": "refresh-1",
        "is_verified": True,
        "success": True,
        "token": "",
        "p12Base64": "",
        "p12Password": "",
    }

    refresh_response = await async_client.post(
        "/v1/users/auth/login/refresh",
        headers={"Authorization": f"Bearer {state.refresh_token}"},
    )

    assert refresh_response.status_code == 200
    assert refresh_response.json() == {
        "access_token": "access-2",
        "refresh_token": "refresh-2",
    }

    me_response = await async_client.get(
        "/v1/users/me",
        headers={"Authorization": f"Bearer {state.access_token}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["id"] == str(user.id)



from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi.routing import APIRoute
import pytest

from src.core.limiter.depends import RateLimiter
from src.core.schemas import SuccessResponse, TokenModel
from src.user.auth.dependencies import (
    AuthenticatedUser,
    get_access_by_refresh_token,
    get_current_user_with_session,
)
from src.user.auth.jwt_payload_schema import JWTPayload
from src.user.auth.routers import router
from src.user.auth.schemas import LoginTokenModel, RegisterTokenModel
from src.user.auth.usecases.get_access_by_refresh import (
    get_tokens_by_refresh_user_use_case,
)
from src.user.auth.usecases.login import get_login_user_use_case
from src.user.auth.usecases.logout import get_logout_use_case
from src.user.auth.usecases.register import get_register_use_case
from tests.factories.token_factory import build_refresh_payload
from tests.factories.user_factory import build_user
from tests.helpers.limiter import noop_rate_limiter
from tests.helpers.overrides import DependencyOverrides
from tests.helpers.providers import ProvideValue


class FakeUseCase:
    def __init__(self, result) -> None:
        self.execute = AsyncMock(return_value=result)


def _get_auth_route(*, path: str, method: str) -> APIRoute:
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path == path and method in route.methods:
            return route

    raise AssertionError(f"Route {method} {path} not found")


def _get_route_rate_limiters(route: APIRoute) -> list[RateLimiter]:
    return [
        dependency.call
        for dependency in route.dependant.dependencies
        if isinstance(dependency.call, RateLimiter)
    ]


@pytest.fixture(autouse=True)
def disable_rate_limiter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.core.limiter.depends.RateLimiter.__call__",
        noop_rate_limiter,
    )


@pytest.mark.asyncio
async def test_register_endpoint(
    async_client,
    dependency_overrides: DependencyOverrides,
) -> None:
    # Ro'yxatdan o'tish faqat mobil ilovadan: login + parol. Javob — Face-ID
    # verifikatsiyasi uchun token va client p12 (mobil kutgan camelCase kalitlar)
    result = RegisterTokenModel(access_token="a", p12_base64="p12", p12_password="pw")
    dependency_overrides.set(get_register_use_case, ProvideValue(FakeUseCase(result)))

    response = await async_client.post(
        "/v1/users/auth/register",
        json={"username": "john_doe", "password": "StrongPass1!"},
    )

    assert response.status_code == 201
    assert response.json() == {
        "success": True,
        "accessToken": "a",
        "p12Base64": "p12",
        "p12Password": "pw",
    }


@pytest.mark.asyncio
async def test_login_endpoint(
    async_client,
    dependency_overrides: DependencyOverrides,
) -> None:
    tokens = LoginTokenModel(access_token="a", refresh_token="r", is_verified=True)
    dependency_overrides.set(get_login_user_use_case, ProvideValue(FakeUseCase(tokens)))

    response = await async_client.post(
        "/v1/users/auth/login",
        json={"username": "user", "password": "StrongPass1!"},
    )

    assert response.status_code == 200
    # Login javobida `is_verified` ham bor — mobil shu bayroqqa qarab
    # chatga yoki Face-ID verifikatsiyasiga yo'naltiradi
    # Tasdiqlangan user: tokenlar to'la, Face-ID maydonlari bo'sh
    assert response.json() == {
        "access_token": "a",
        "refresh_token": "r",
        "is_verified": True,
        "success": True,
        "token": "",
        "p12Base64": "",
        "p12Password": "",
    }


@pytest.mark.asyncio
async def test_refresh_endpoint(
    async_client,
    dependency_overrides: DependencyOverrides,
) -> None:
    user = build_user()
    payload: JWTPayload = build_refresh_payload(str(user.id))
    dependency_overrides.set(get_access_by_refresh_token, ProvideValue((user, payload)))
    tokens = TokenModel(access_token="a", refresh_token="r")
    dependency_overrides.set(
        get_tokens_by_refresh_user_use_case, ProvideValue(FakeUseCase(tokens))
    )

    response = await async_client.post("/v1/users/auth/login/refresh")

    assert response.status_code == 200
    assert response.json() == {"access_token": "a", "refresh_token": "r"}


@pytest.mark.asyncio
async def test_logout_endpoint(
    async_client,
    dependency_overrides: DependencyOverrides,
) -> None:
    user = build_user()
    authenticated = AuthenticatedUser(
        user=user,
        session_id="session-1",
    )
    dependency_overrides.set(
        get_current_user_with_session,
        ProvideValue(authenticated),
    )
    logout_use_case = FakeUseCase(SuccessResponse(success=True))
    dependency_overrides.set(get_logout_use_case, ProvideValue(logout_use_case))

    response = await async_client.post("/v1/users/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"success": True}
    logout_use_case.execute.assert_awaited_once_with(
        user_id=str(user.id),
        session_id="session-1",
        terminate_all_sessions=False,
    )


@pytest.mark.asyncio
async def test_logout_endpoint_can_terminate_all_sessions(
    async_client,
    dependency_overrides: DependencyOverrides,
) -> None:
    user = build_user()
    authenticated = AuthenticatedUser(
        user=user,
        session_id="session-1",
    )
    dependency_overrides.set(
        get_current_user_with_session,
        ProvideValue(authenticated),
    )
    logout_use_case = FakeUseCase(SuccessResponse(success=True))
    dependency_overrides.set(get_logout_use_case, ProvideValue(logout_use_case))

    response = await async_client.post(
        "/v1/users/auth/logout",
        json={"terminate_all_sessions": True},
    )

    assert response.status_code == 200
    assert response.json() == {"success": True}
    logout_use_case.execute.assert_awaited_once_with(
        user_id=str(user.id),
        session_id="session-1",
        terminate_all_sessions=True,
    )



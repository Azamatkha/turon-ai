from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import jwt
import pytest

from src.core.errors.exceptions import (
    InstanceProcessingException,
    PermissionDeniedException,
)
from src.core.schemas import SuccessResponse, TokenModel
from src.main.config import config
from src.user.auth.usecases.get_access_by_refresh import GetTokensByRefreshUserUseCase
from src.user.auth.usecases.logout import LogoutUseCase
from src.user.models import User
from tests.factories.token_factory import (
    build_refresh_payload,
)
from tests.factories.user_factory import build_user
from tests.fakes.db import FakeAsyncSession, FakeUnitOfWork
from tests.fakes.redis import InMemoryRedis


class FakeUsersRepository:
    def __init__(
        self,
        user: User | None = None,
        updated_user: User | None = None,
    ) -> None:
        self._user = user
        self._updated_user = updated_user or user
        self.create = AsyncMock(side_effect=self._create)
        self.get_single = AsyncMock(side_effect=self._get_single)
        self.update = AsyncMock(side_effect=self._update)

    async def _create(self, session: FakeAsyncSession, data: dict) -> User:
        if self._user:
            return self._user
        return build_user(
            email=data["email"],
            username=data["username"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            phone_number=data["phone_number"],
            password=data.get("password", "StrongPass1!"),
        )

    async def _get_single(
        self, session: FakeAsyncSession, **filters: object
    ) -> User | None:
        return self._user

    async def _update(
        self, session: FakeAsyncSession, data: dict, **filters: object
    ) -> User | None:
        return self._updated_user


def build_uow(
    session: FakeAsyncSession,
    users_repo: FakeUsersRepository,
) -> FakeUnitOfWork:
    return FakeUnitOfWork(session=session, repositories={"users": users_repo})


@pytest.mark.asyncio
async def test_get_tokens_by_refresh_user_usecase_success(
    fake_redis: InMemoryRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = build_user(is_verified=True, is_active=True)
    payload = build_refresh_payload(str(user.id))
    refresh_token = jwt.encode(
        payload,
        config.jwt.JWT_USER_SECRET_KEY,
        config.jwt.ALGORITHM,
    )
    access_token = "access-token"

    rotate_mock = AsyncMock(return_value=refresh_token)
    create_access_mock = AsyncMock(return_value=access_token)
    monkeypatch.setattr(
        "src.user.auth.usecases.get_access_by_refresh.rotate_refresh_token",
        rotate_mock,
    )
    monkeypatch.setattr(
        "src.user.auth.usecases.get_access_by_refresh.create_access_token",
        create_access_mock,
    )

    use_case = GetTokensByRefreshUserUseCase(redis_client=fake_redis)
    result = await use_case.execute(user=user, old_token_payload=payload)

    assert isinstance(result, TokenModel)
    assert result.refresh_token == refresh_token
    assert result.access_token == access_token
    rotate_mock.assert_awaited_once()
    create_access_mock.assert_awaited_once_with(
        {"sub": str(user.id)},
        redis_client=fake_redis,
        session_id=payload["session_id"],
    )


@pytest.mark.asyncio
async def test_get_tokens_by_refresh_user_usecase_blocked(
    fake_redis: InMemoryRedis,
) -> None:
    user = build_user(is_verified=True, is_active=False)
    payload = build_refresh_payload(str(user.id))

    use_case = GetTokensByRefreshUserUseCase(redis_client=fake_redis)

    with pytest.raises(PermissionDeniedException, match="User is blocked"):
        await use_case.execute(user=user, old_token_payload=payload)


@pytest.mark.asyncio
async def test_get_tokens_by_refresh_user_usecase_unverified(
    fake_redis: InMemoryRedis,
) -> None:
    user = build_user(is_verified=False, is_active=True)
    payload = build_refresh_payload(str(user.id))

    use_case = GetTokensByRefreshUserUseCase(redis_client=fake_redis)

    with pytest.raises(InstanceProcessingException, match="User is not verified"):
        await use_case.execute(user=user, old_token_payload=payload)


USER_ID = "3f1b2c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d"


def build_logout_uow(fake_session: FakeAsyncSession) -> FakeUnitOfWork:
    """Logout "logout" hodisasini yozadi va last_seen_at ni tozalaydi."""
    return FakeUnitOfWork(
        session=fake_session,
        repositories={
            "login_events": SimpleNamespace(create=AsyncMock()),
            "users": SimpleNamespace(update=AsyncMock()),
        },
    )


@pytest.mark.asyncio
async def test_logout_usecase_invalidates_current_session(
    fake_redis: InMemoryRedis,
    fake_session: FakeAsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalidate_mock = AsyncMock()
    monkeypatch.setattr(
        "src.user.auth.usecases.logout.invalidate_user_session",
        invalidate_mock,
    )

    uow = build_logout_uow(fake_session)
    use_case = LogoutUseCase(redis_client=fake_redis, uow=uow)
    result = await use_case.execute(
        user_id=USER_ID,
        session_id="session-1",
    )

    assert result == SuccessResponse(success=True)
    invalidate_mock.assert_awaited_once_with(
        USER_ID,
        "session-1",
        fake_redis,
    )
    # "So'nggi faollik" uchun logout hodisasi yozildi
    uow.login_events.create.assert_awaited_once()
    assert uow.login_events.create.await_args.args[1]["action"] == "logout"


@pytest.mark.asyncio
async def test_logout_usecase_can_invalidate_all_sessions(
    fake_redis: InMemoryRedis,
    fake_session: FakeAsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalidate_mock = AsyncMock()
    monkeypatch.setattr(
        "src.user.auth.usecases.logout.invalidate_all_user_sessions",
        invalidate_mock,
    )

    use_case = LogoutUseCase(redis_client=fake_redis, uow=build_logout_uow(fake_session))
    result = await use_case.execute(
        user_id=USER_ID,
        session_id="session-1",
        terminate_all_sessions=True,
    )

    assert result == SuccessResponse(success=True)
    invalidate_mock.assert_awaited_once_with(USER_ID, fake_redis)



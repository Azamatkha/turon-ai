from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.core.errors.exceptions import InstanceProcessingException
from src.core.schemas import SuccessResponse
from src.user.auth.schemas import UserNewPassword
from src.user.usecases.update_password import UpdateUserPasswordUseCase
from tests.factories.user_factory import build_user
from tests.fakes.db import FakeAsyncSession, FakeUnitOfWork
from tests.fakes.redis import InMemoryRedis

# `build_user()` shu parolni hash qilib qo'yadi — joriy parol tekshiruvi
# muvaffaqiyatli o'tishi uchun testlar aynan shuni yuboradi.
CURRENT_PASSWORD = "password"


def new_password_payload(
    current: str = CURRENT_PASSWORD, new: str = "StrongPass1!"
) -> UserNewPassword:
    return UserNewPassword(current_password=current, password=new)


class FakeUsersRepository:
    def __init__(self, updated_user):
        # Use-case avval `get_single` bilan foydalanuvchini yuklab, joriy
        # parolini tekshiradi; keyingina `update` chaqiriladi.
        self.get_single = AsyncMock(return_value=updated_user)
        self.update = AsyncMock(return_value=updated_user)


def build_uow(
    session: FakeAsyncSession, users_repo: FakeUsersRepository
) -> FakeUnitOfWork:
    return FakeUnitOfWork(session=session, repositories={"users": users_repo})


@pytest.mark.asyncio
async def test_update_password_user_not_found(
    fake_session: FakeAsyncSession,
    fake_redis: InMemoryRedis,
) -> None:
    users_repo = FakeUsersRepository(updated_user=None)
    uow = build_uow(fake_session, users_repo)
    use_case = UpdateUserPasswordUseCase(uow=uow, redis_client=fake_redis)

    result = await use_case.execute(
        data=new_password_payload(),
        user_id=build_user().id,
    )

    assert result == SuccessResponse(success=False)
    uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_password_wrong_current_password(
    fake_session: FakeAsyncSession,
    fake_redis: InMemoryRedis,
) -> None:
    """Joriy parol noto'g'ri bo'lsa parol O'ZGARMAYDI.

    Bu — o'g'irlangan token bilan hisobni egallab olishga qarshi himoya:
    token bo'lsa ham, eski parolni bilmasdan yangisini qo'yib bo'lmaydi.
    """
    user = build_user()
    users_repo = FakeUsersRepository(updated_user=user)
    uow = build_uow(fake_session, users_repo)
    use_case = UpdateUserPasswordUseCase(uow=uow, redis_client=fake_redis)

    with pytest.raises(InstanceProcessingException):
        await use_case.execute(
            data=new_password_payload(current="notmypassword"),
            user_id=user.id,
        )

    users_repo.update.assert_not_awaited()
    uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_password_success(
    fake_session: FakeAsyncSession,
    fake_redis: InMemoryRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = build_user()
    users_repo = FakeUsersRepository(updated_user=user)
    uow = build_uow(fake_session, users_repo)
    invalidate_mock = AsyncMock()
    monkeypatch.setattr(
        "src.user.usecases.update_password.invalidate_all_user_sessions",
        invalidate_mock,
    )

    use_case = UpdateUserPasswordUseCase(uow=uow, redis_client=fake_redis)
    result = await use_case.execute(
        data=new_password_payload(),
        user_id=user.id,
    )

    assert result == SuccessResponse(success=True)
    uow.commit.assert_awaited_once()
    uow.flush.assert_awaited_once()
    invalidate_mock.assert_awaited_once_with(str(user.id), fake_redis)


@pytest.mark.asyncio
async def test_update_password_redis_failure_skips_commit(
    fake_session: FakeAsyncSession,
    fake_redis: InMemoryRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = build_user()
    users_repo = FakeUsersRepository(updated_user=user)
    uow = build_uow(fake_session, users_repo)
    invalidate_mock = AsyncMock(side_effect=RuntimeError("redis down"))
    monkeypatch.setattr(
        "src.user.usecases.update_password.invalidate_all_user_sessions",
        invalidate_mock,
    )

    use_case = UpdateUserPasswordUseCase(uow=uow, redis_client=fake_redis)

    with pytest.raises(RuntimeError, match="redis down"):
        await use_case.execute(
            data=new_password_payload(),
            user_id=user.id,
        )

    uow.flush.assert_awaited_once()
    uow.commit.assert_not_awaited()
    uow.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_password_commit_failure_after_invalidation(
    fake_session: FakeAsyncSession,
    fake_redis: InMemoryRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = build_user()
    users_repo = FakeUsersRepository(updated_user=user)
    uow = build_uow(fake_session, users_repo)
    uow.commit = AsyncMock(side_effect=RuntimeError("db down"))
    invalidate_mock = AsyncMock()
    monkeypatch.setattr(
        "src.user.usecases.update_password.invalidate_all_user_sessions",
        invalidate_mock,
    )

    use_case = UpdateUserPasswordUseCase(uow=uow, redis_client=fake_redis)

    with pytest.raises(RuntimeError, match="db down"):
        await use_case.execute(
            data=new_password_payload(),
            user_id=user.id,
        )

    invalidate_mock.assert_awaited_once_with(str(user.id), fake_redis)
    uow.flush.assert_awaited_once()
    uow.rollback.assert_awaited_once()

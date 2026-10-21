import pytest

from src.core.errors.exceptions import InstanceNotFoundException
from src.user.auth.usecases.check_user import CheckUserVerifiedUseCase
from src.user.models import User
from tests.factories.user_factory import build_user
from tests.fakes.db import FakeAsyncSession, FakeUnitOfWork


class FakeUserRepository:
    def __init__(self, user: User | None) -> None:
        self._user = user
        self.calls: list[str] = []

    async def get_by_username(
        self, session: FakeAsyncSession, username: str
    ) -> User | None:
        self.calls.append(username)
        return self._user


def build_uow(user: User | None, session: FakeAsyncSession) -> FakeUnitOfWork:
    return FakeUnitOfWork(
        session=session,
        repositories={"users": FakeUserRepository(user)},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("verified", [True, False])
async def test_check_user_returns_verified_flag(
    fake_session: FakeAsyncSession, verified: bool
) -> None:
    user = build_user()
    user.is_verified = verified
    uow = build_uow(user, fake_session)

    result = await CheckUserVerifiedUseCase(uow=uow).execute(username="a.karimov")

    assert result.is_verified is verified
    assert uow.users.calls == ["a.karimov"]


@pytest.mark.asyncio
async def test_check_user_not_found_raises(fake_session: FakeAsyncSession) -> None:
    uow = build_uow(None, fake_session)

    with pytest.raises(InstanceNotFoundException):
        await CheckUserVerifiedUseCase(uow=uow).execute(username="nobody")

import pytest

from src.core.database.filters import FilterCondition
from src.user.repositories import UserRepository
from tests.fakes.db import FakeAsyncSession


@pytest.mark.asyncio
async def test_batch_soft_delete_raises_value_error_on_empty_filters(
    fake_session: FakeAsyncSession,
) -> None:
    repo = UserRepository()

    with pytest.raises(
        ValueError, match="At least one filter condition must be provided"
    ):
        await repo.batch_soft_delete(fake_session, filters=FilterCondition())

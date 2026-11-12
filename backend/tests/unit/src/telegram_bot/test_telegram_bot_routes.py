from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.main.config import config
from src.telegram_bot.schemas import (
    BotSyncResult,
    TgMessagePage,
    TgUserPage,
    TgUserView,
)
from src.telegram_bot.usecases import (
    get_list_tg_messages_use_case,
    get_list_tg_users_use_case,
    get_sync_bot_data_use_case,
)
from src.user.auth.dependencies import get_current_user
from src.user.enums import UserRole
from tests.factories.user_factory import build_user
from tests.helpers.overrides import DependencyOverrides
from tests.helpers.providers import ProvideValue

BOT_KEY = "test-bot-key"
NOW = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)

SYNC_BODY = {
    "users": [
        {"telegram_id": 111, "full_name": "Ali", "first_seen_at": NOW.isoformat()}
    ],
    "messages": [
        {
            "bot_message_id": 1,
            "telegram_id": 111,
            "direction": "in",
            "status": "new",
            "text": "salom",
            "sent_at": NOW.isoformat(),
        }
    ],
}


class FakeUseCase:
    def __init__(self, result) -> None:
        self.execute = AsyncMock(return_value=result)


def _tg_user() -> TgUserView:
    return TgUserView(
        id=uuid4(),
        telegram_id=111,
        username="ali",
        full_name="Ali",
        language="uz",
        phone="+998901234567",
        reg_step="done",
        is_banned=False,
        first_seen_at=NOW,
        last_message_at=NOW,
        messages_count=3,
        pending_count=1,
    )


@pytest.fixture
def bot_key(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(config.telegram_bot, "TELEGRAM_BOT_API_KEY", BOT_KEY)
    return BOT_KEY


@pytest.mark.asyncio
async def test_sync_without_key_is_unauthorized(
    async_client, dependency_overrides: DependencyOverrides, bot_key: str
) -> None:
    use_case = FakeUseCase(BotSyncResult(users=1, messages=1))
    dependency_overrides.set(get_sync_bot_data_use_case, ProvideValue(use_case))

    response = await async_client.post("/v1/telegram-bot/sync", json=SYNC_BODY)

    assert response.status_code == 401
    use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_with_wrong_key_is_unauthorized(
    async_client, dependency_overrides: DependencyOverrides, bot_key: str
) -> None:
    use_case = FakeUseCase(BotSyncResult(users=1, messages=1))
    dependency_overrides.set(get_sync_bot_data_use_case, ProvideValue(use_case))

    response = await async_client.post(
        "/v1/telegram-bot/sync", json=SYNC_BODY, headers={"X-Bot-Key": "wrong"}
    )

    assert response.status_code == 401
    use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_disabled_when_key_not_configured(
    async_client, dependency_overrides: DependencyOverrides, monkeypatch
) -> None:
    monkeypatch.setattr(config.telegram_bot, "TELEGRAM_BOT_API_KEY", "")
    use_case = FakeUseCase(BotSyncResult(users=1, messages=1))
    dependency_overrides.set(get_sync_bot_data_use_case, ProvideValue(use_case))

    response = await async_client.post(
        "/v1/telegram-bot/sync", json=SYNC_BODY, headers={"X-Bot-Key": "anything"}
    )

    assert response.status_code == 403
    use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_with_valid_key(
    async_client, dependency_overrides: DependencyOverrides, bot_key: str
) -> None:
    use_case = FakeUseCase(BotSyncResult(users=1, messages=1))
    dependency_overrides.set(get_sync_bot_data_use_case, ProvideValue(use_case))

    response = await async_client.post(
        "/v1/telegram-bot/sync", json=SYNC_BODY, headers={"X-Bot-Key": bot_key}
    )

    assert response.status_code == 200
    assert response.json() == {"users": 1, "messages": 1, "skipped_messages": 0}
    sent = use_case.execute.await_args.args[0]
    assert sent.users[0].telegram_id == 111
    assert sent.messages[0].text == "salom"


@pytest.mark.asyncio
async def test_admin_lists_tg_users(
    async_client, dependency_overrides: DependencyOverrides
) -> None:
    dependency_overrides.set(
        get_current_user, ProvideValue(build_user(role=UserRole.ADMIN))
    )
    use_case = FakeUseCase(TgUserPage(items=[_tg_user()], total=1))
    dependency_overrides.set(get_list_tg_users_use_case, ProvideValue(use_case))

    response = await async_client.get(
        "/v1/admin/telegram-bot/users", params={"search": "ali", "page": 2}
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["pending_count"] == 1
    use_case.execute.assert_awaited_once_with(
        search="ali", page=2, size=20, status=None, sort="joined"
    )


@pytest.mark.asyncio
async def test_admin_lists_tg_users_with_filter_and_sort(
    async_client, dependency_overrides: DependencyOverrides
) -> None:
    dependency_overrides.set(
        get_current_user, ProvideValue(build_user(role=UserRole.ADMIN))
    )
    use_case = FakeUseCase(TgUserPage(items=[], total=0))
    dependency_overrides.set(get_list_tg_users_use_case, ProvideValue(use_case))

    response = await async_client.get(
        "/v1/admin/telegram-bot/users",
        params={"status": "pending", "sort": "last_message"},
    )

    assert response.status_code == 200
    use_case.execute.assert_awaited_once_with(
        search=None, page=1, size=20, status="pending", sort="last_message"
    )
    bad = await async_client.get(
        "/v1/admin/telegram-bot/users", params={"status": "nimadir"}
    )
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_plain_user_cannot_list_tg_users(
    async_client, dependency_overrides: DependencyOverrides
) -> None:
    dependency_overrides.set(get_current_user, ProvideValue(build_user()))
    use_case = FakeUseCase(TgUserPage(items=[], total=0))
    dependency_overrides.set(get_list_tg_users_use_case, ProvideValue(use_case))

    response = await async_client.get("/v1/admin/telegram-bot/users")

    assert response.status_code == 403
    use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_lists_tg_messages(
    async_client, dependency_overrides: DependencyOverrides
) -> None:
    dependency_overrides.set(
        get_current_user, ProvideValue(build_user(role=UserRole.MODERATOR))
    )
    user = _tg_user()
    use_case = FakeUseCase(TgMessagePage(user=user, items=[], total=0))
    dependency_overrides.set(get_list_tg_messages_use_case, ProvideValue(use_case))

    response = await async_client.get(
        f"/v1/admin/telegram-bot/users/{user.id}/messages"
    )

    assert response.status_code == 200
    assert response.json()["user"]["telegram_id"] == 111
    use_case.execute.assert_awaited_once_with(user_id=user.id, page=1, size=50)

from types import SimpleNamespace

import pytest

from src.core.errors.exceptions import InstanceNotFoundException
from src.user.auth.redis_keys import auth_redis_keys
from src.user.auth.sessions import describe_device, list_user_sessions, touch_session
from src.user.auth.usecases.sessions import (
    ListActiveSessionsUseCase,
    RevokeOtherSessionsUseCase,
    RevokeSessionUseCase,
)
from tests.fakes.redis import InMemoryRedis

CHROME_WIN = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)


def _request(ua: str, ip: str) -> SimpleNamespace:
    return SimpleNamespace(headers={"user-agent": ua}, client=SimpleNamespace(host=ip))


async def _login(redis: InMemoryRedis, user: str, sid: str, ua: str, ip: str) -> None:
    """Login'ni taqlid qiladi: refresh kaliti + bitta so'rov (meta yoziladi)."""
    await redis.set(auth_redis_keys.access(user, sid), "a", ex=600)
    await redis.set(auth_redis_keys.refresh(user, sid), "r", ex=600)
    await touch_session(redis, user, sid, _request(ua, ip))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("ua", "expected"),
    [
        (CHROME_WIN, "Chrome · Windows"),
        ("Mozilla/5.0 (Windows NT 10.0) Chrome/130.0 Edg/130.0", "Edge · Windows"),
        ("Mozilla/5.0 (Android 14) Firefox/131.0", "Firefox · Android"),
        ("Dart/3.5 (dart:io)", "Turon AI app"),
        ("okhttp/4.12.0 Android", "Turon AI app · Android"),
        ("", ""),
    ],
)
def test_describe_device(ua: str, expected: str) -> None:
    assert describe_device(ua) == expected


@pytest.mark.asyncio
async def test_list_sessions_marks_current_first() -> None:
    redis = InMemoryRedis()
    await _login(redis, "u1", "s1", CHROME_WIN, "10.0.0.1")
    await _login(redis, "u1", "s2", "Dart/3.5", "10.0.0.2")
    await _login(redis, "u2", "x1", CHROME_WIN, "10.0.0.3")  # begona user

    views = await ListActiveSessionsUseCase(redis).execute("u1", "s1")  # type: ignore[arg-type]

    assert [v.session_id for v in views] == ["s1", "s2"]
    assert views[0].current and not views[1].current
    assert views[0].device == "Chrome · Windows" and views[0].ip == "10.0.0.1"
    assert views[0].created_at is not None and views[0].last_seen_at is not None


@pytest.mark.asyncio
async def test_touch_keeps_created_and_updates_ip() -> None:
    redis = InMemoryRedis()
    await _login(redis, "u1", "s1", CHROME_WIN, "10.0.0.1")
    created = (await redis.hgetall(auth_redis_keys.session_meta("u1", "s1")))["created"]
    await touch_session(redis, "u1", "s1", _request(CHROME_WIN, "10.0.0.9"))  # type: ignore[arg-type]
    meta = await redis.hgetall(auth_redis_keys.session_meta("u1", "s1"))
    assert meta["created"] == created
    assert meta["ip"] == "10.0.0.9"


@pytest.mark.asyncio
async def test_revoke_other_sessions_keeps_current() -> None:
    redis = InMemoryRedis()
    for sid in ("s1", "s2", "s3"):
        await _login(redis, "u1", sid, CHROME_WIN, "10.0.0.1")

    result = await RevokeOtherSessionsUseCase(redis).execute("u1", "s2")  # type: ignore[arg-type]

    assert result.revoked == 2
    assert [s.session_id for s in await list_user_sessions(redis, "u1")] == ["s2"]  # type: ignore[arg-type]
    assert await redis.exists(auth_redis_keys.access("u1", "s1")) == 0
    assert await redis.exists(auth_redis_keys.session_meta("u1", "s1")) == 0


@pytest.mark.asyncio
async def test_revoke_session_only_own() -> None:
    redis = InMemoryRedis()
    await _login(redis, "u1", "s1", CHROME_WIN, "10.0.0.1")
    await _login(redis, "u2", "x1", CHROME_WIN, "10.0.0.2")

    # Begona userning seansini yopib bo'lmaydi
    with pytest.raises(InstanceNotFoundException):
        await RevokeSessionUseCase(redis).execute("u1", "x1")  # type: ignore[arg-type]
    assert await redis.exists(auth_redis_keys.refresh("u2", "x1")) == 1

    result = await RevokeSessionUseCase(redis).execute("u1", "s1")  # type: ignore[arg-type]
    assert result.revoked == 1
    assert await redis.exists(auth_redis_keys.refresh("u1", "s1")) == 0

import pytest

from src.core.errors.exceptions import TooManyRequestsException, UnauthorizedException
from src.user.auth.redis_keys import auth_redis_keys
import src.user.auth.security as security
from src.user.auth.usecases.check_face_token import CheckFaceTokenUseCase
from tests.fakes.redis import InMemoryRedis

TEST_JWT_USER_SECRET_KEY = "test-jwt-user-secret-key-not-real"


@pytest.fixture(autouse=True)
def _patch_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        security.config.jwt, "JWT_USER_SECRET_KEY", TEST_JWT_USER_SECRET_KEY
    )
    monkeypatch.setattr(security.config.jwt, "ALGORITHM", "HS256")
    monkeypatch.setattr(security.config.jwt, "ACCESS_TOKEN_EXPIRE_MINUTES", 5)
    monkeypatch.setattr(security.config.jwt, "FACE_ID_TOKEN_EXPIRE_MINUTES", 20)
    monkeypatch.setattr(security.config.jwt, "FACE_ID_RATE_LIMIT_SECONDS", 15)


async def _face_token(redis: InMemoryRedis, user_id: str) -> str:
    return await security.create_access_token(
        {"sub": user_id}, redis_client=redis, for_face_id=True
    )


@pytest.mark.asyncio
async def test_second_request_within_window_is_rate_limited(
    fake_redis: InMemoryRedis,
) -> None:
    """
    Given: bitta user'ning yaroqli Face-ID tokeni.
    When: tekshiruv 15 soniya ichida ikki marta chaqiriladi.
    Then: birinchisi o'tadi, ikkinchisi 429 (Retry-After bilan).
    """
    use_case = CheckFaceTokenUseCase(redis_client=fake_redis)
    token = await _face_token(fake_redis, "11111111-1111-1111-1111-111111111111")

    first = await use_case.execute(token)
    assert first.success is True

    with pytest.raises(TooManyRequestsException) as exc_info:
        await use_case.execute(token)
    assert exc_info.value.retry_after is not None
    assert 1 <= exc_info.value.retry_after <= 15


@pytest.mark.asyncio
async def test_new_token_for_same_user_does_not_bypass_limit(
    fake_redis: InMemoryRedis,
) -> None:
    """Qayta login qilib yangi token olish cheklovni aylanib o'tmaydi."""
    use_case = CheckFaceTokenUseCase(redis_client=fake_redis)
    user_id = "11111111-1111-1111-1111-111111111111"

    await use_case.execute(await _face_token(fake_redis, user_id))

    with pytest.raises(TooManyRequestsException):
        await use_case.execute(await _face_token(fake_redis, user_id))


@pytest.mark.asyncio
async def test_different_users_do_not_block_each_other(
    fake_redis: InMemoryRedis,
) -> None:
    use_case = CheckFaceTokenUseCase(redis_client=fake_redis)

    a = await use_case.execute(
        await _face_token(fake_redis, "11111111-1111-1111-1111-111111111111")
    )
    b = await use_case.execute(
        await _face_token(fake_redis, "22222222-2222-2222-2222-222222222222")
    )

    assert a.success is True
    assert b.success is True


@pytest.mark.asyncio
async def test_invalid_token_is_401_and_does_not_consume_limit(
    fake_redis: InMemoryRedis,
) -> None:
    """
    Given: yaroqsiz token.
    When: tekshiruv chaqiriladi.
    Then: 401; rate kaliti yozilmaydi — keyingi yaroqli so'rov o'tadi.
    """
    use_case = CheckFaceTokenUseCase(redis_client=fake_redis)
    user_id = "11111111-1111-1111-1111-111111111111"

    with pytest.raises(UnauthorizedException):
        await use_case.execute("not-a-jwt")

    assert await fake_redis.exists(auth_redis_keys.face_id_rate_limit(user_id)) == 0
    result = await use_case.execute(await _face_token(fake_redis, user_id))
    assert result.success is True


@pytest.mark.asyncio
async def test_request_passes_again_after_window(fake_redis: InMemoryRedis) -> None:
    """15 soniya o'tgach (rate kaliti muddati tugagach) yana o'tadi."""
    use_case = CheckFaceTokenUseCase(redis_client=fake_redis)
    user_id = "11111111-1111-1111-1111-111111111111"
    token = await _face_token(fake_redis, user_id)

    await use_case.execute(token)
    # Vaqt o'tishini taqlid qilish: kalit muddatini tugatamiz
    await fake_redis.delete(auth_redis_keys.face_id_rate_limit(user_id))

    result = await use_case.execute(token)
    assert result.success is True

from __future__ import annotations

import fnmatch
import hashlib
import time
from typing import Any

import redis.exceptions as redis_exc

from src.user.auth.redis_scripts import ROTATE_REFRESH_TOKEN_SCRIPT


def _normalize_key(key: str | bytes) -> str:
    if isinstance(key, bytes):
        return key.decode("utf-8")
    return key


def _normalize_value(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _now() -> float:
    return time.monotonic()


class InMemoryRedis:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._expires: dict[str, float] = {}
        self._scripts: dict[str, str] = {}
        self._evalsha_overrides: dict[str, int] = {}
        self.closed = False

    def set_evalsha_result(self, key: str, result: int) -> None:
        self._evalsha_overrides[key] = result

    def clear_evalsha_overrides(self) -> None:
        self._evalsha_overrides.clear()

    def _purge_expired(self, key: str) -> None:
        expires_at = self._expires.get(key)
        if expires_at is None:
            return
        if _now() >= expires_at:
            self._store.pop(key, None)
            self._expires.pop(key, None)

    async def get(self, key: str | bytes) -> str | None:
        key_norm = _normalize_key(key)
        self._purge_expired(key_norm)
        return self._store.get(key_norm)

    async def set(
        self,
        key: str | bytes,
        value: Any,
        *,
        ex: int | None = None,
        px: int | None = None,
        nx: bool = False,
    ) -> bool | None:
        key_norm = _normalize_key(key)
        if nx:
            self._purge_expired(key_norm)
            if key_norm in self._store:
                return None
        self._store[key_norm] = _normalize_value(value)
        if ex is not None:
            self._expires[key_norm] = _now() + int(ex)
        elif px is not None:
            self._expires[key_norm] = _now() + (int(px) / 1000)
        else:
            self._expires.pop(key_norm, None)
        return True

    async def setex(self, key: str | bytes, time_seconds: int, value: Any) -> bool:
        return await self.set(key, value, ex=time_seconds)

    async def delete(self, *keys: str | bytes) -> int:
        deleted = 0
        for key in keys:
            key_norm = _normalize_key(key)
            self._purge_expired(key_norm)
            if key_norm in self._store:
                self._store.pop(key_norm, None)
                self._expires.pop(key_norm, None)
                deleted += 1
        return deleted

    async def exists(self, key: str | bytes) -> int:
        key_norm = _normalize_key(key)
        self._purge_expired(key_norm)
        return int(key_norm in self._store)

    async def expire(self, key: str | bytes, seconds: int) -> bool:
        key_norm = _normalize_key(key)
        self._purge_expired(key_norm)
        if key_norm not in self._store:
            return False
        self._expires[key_norm] = _now() + int(seconds)
        return True

    async def ttl(self, key: str | bytes) -> int:
        key_norm = _normalize_key(key)
        self._purge_expired(key_norm)
        if key_norm not in self._store:
            return -2
        expires_at = self._expires.get(key_norm)
        if expires_at is None:
            return -1
        return max(0, int(expires_at - _now()))

    async def incr(self, key: str | bytes) -> int:
        key_norm = _normalize_key(key)
        self._purge_expired(key_norm)
        value = int(self._store.get(key_norm) or 0) + 1
        self._store[key_norm] = str(value)
        return value

    # ---- Hash (seans meta-ma'lumoti uchun: src/user/auth/sessions.py) ----

    def _hash(self, key: str | bytes) -> dict[str, str]:
        key_norm = _normalize_key(key)
        self._purge_expired(key_norm)
        current = self._store.get(key_norm)
        if not isinstance(current, dict):
            current = {}
            self._store[key_norm] = current  # type: ignore[assignment]
        return current

    async def hset(
        self, key: str | bytes, field: str | None = None, value: Any = None,
        mapping: dict[str, Any] | None = None,
    ) -> int:
        h = self._hash(key)
        items = dict(mapping or {})
        if field is not None:
            items[field] = value
        added = sum(1 for f in items if f not in h)
        h.update({f: _normalize_value(v) for f, v in items.items()})
        return added

    async def hsetnx(self, key: str | bytes, field: str, value: Any) -> int:
        h = self._hash(key)
        if field in h:
            return 0
        h[field] = _normalize_value(value)
        return 1

    async def hgetall(self, key: str | bytes) -> dict[str, str]:
        key_norm = _normalize_key(key)
        self._purge_expired(key_norm)
        current = self._store.get(key_norm)
        return dict(current) if isinstance(current, dict) else {}

    def pipeline(self, transaction: bool = True) -> "_InMemoryPipeline":
        return _InMemoryPipeline(self)

    async def scan(
        self,
        cursor: int = 0,
        match: str | None = None,
        count: int | None = None,
    ) -> tuple[int, list[str]]:
        for key in list(self._store.keys()):
            self._purge_expired(key)

        keys = list(self._store.keys())
        if match:
            keys = [key for key in keys if fnmatch.fnmatch(key, match)]
        if count is not None:
            keys = keys[:count]
        return 0, keys

    async def script_load(self, script: str) -> str:
        sha = hashlib.sha1(script.encode("utf-8")).hexdigest()
        self._scripts[sha] = script
        return sha

    async def evalsha(
        self,
        sha: str,
        numkeys: int,
        *keys_and_args: Any,
    ) -> int:
        if sha not in self._scripts:
            raise redis_exc.NoScriptError(
                "NOSCRIPT No matching script. Please use EVAL."
            )

        keys = [_normalize_key(key) for key in keys_and_args[:numkeys]]
        key = keys[0] if keys else ""
        if key in self._evalsha_overrides:
            return self._evalsha_overrides[key]
        return 0

    async def eval(
        self,
        script: str,
        numkeys: int,
        *keys_and_args: Any,
    ) -> str:
        if script.strip() == ROTATE_REFRESH_TOKEN_SCRIPT.strip():
            return await self._eval_rotate_refresh_token(numkeys, *keys_and_args)
        raise NotImplementedError("Script not supported in fake Redis.")

    async def _eval_rotate_refresh_token(
        self,
        numkeys: int,
        *keys_and_args: Any,
    ) -> str:
        if numkeys != 2:
            raise ValueError("ROTATE_REFRESH_TOKEN_SCRIPT expects 2 keys.")

        refresh_key = _normalize_key(keys_and_args[0])
        used_key = _normalize_key(keys_and_args[1])
        expected_jti = _normalize_value(keys_and_args[2])
        used_ttl_seconds = int(keys_and_args[3])

        if await self.exists(used_key):
            return "REUSED"

        stored_jti = await self.get(refresh_key)
        if stored_jti != expected_jti:
            return "INVALID"

        await self.setex(used_key, used_ttl_seconds, "1")
        await self.delete(refresh_key)
        return "OK"

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        self.closed = True


class _InMemoryPipeline:
    """redis.asyncio pipeline'ining soddalashtirilgan nusxasi: buyruqlar
    navbatga yig'iladi va `execute()` da ketma-ket bajariladi."""

    def __init__(self, redis: InMemoryRedis) -> None:
        self._redis = redis
        self._calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def __getattr__(self, name: str) -> Any:
        def queue(*args: Any, **kwargs: Any) -> "_InMemoryPipeline":
            self._calls.append((name, args, kwargs))
            return self

        return queue

    async def execute(self) -> list[Any]:
        results = []
        for name, args, kwargs in self._calls:
            results.append(await getattr(self._redis, name)(*args, **kwargs))
        self._calls.clear()
        return results

    async def __aenter__(self) -> "_InMemoryPipeline":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        self._calls.clear()

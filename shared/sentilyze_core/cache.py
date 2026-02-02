"""Cache client wrapper with async support.

Prefers Redis (if configured and reachable). If Redis is not configured or is
unavailable (common during Scale-to-Zero / MVP), it transparently falls back to
an in-memory LRU+TTL cache so services keep running without errors.
"""

import asyncio
import inspect
import json
import time
from collections import OrderedDict
from typing import Any, Optional, TypeVar, cast

import redis.asyncio as redis

from .config import Settings, get_settings
from .logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class _InMemoryLRUTTLCache:
    """Async-safe in-memory LRU cache with per-key TTL (best-effort fallback)."""

    def __init__(self, max_items: int = 2048) -> None:
        self._max_items = max_items
        self._data: OrderedDict[str, tuple[str, float | None]] = OrderedDict()
        self._lock = asyncio.Lock()

    def _purge_expired(self, now: float) -> None:
        keys_to_delete: list[str] = []
        for k, (_, exp) in self._data.items():
            if exp is None or exp > now:
                break
            keys_to_delete.append(k)
        for k in keys_to_delete:
            self._data.pop(k, None)

    def _evict_if_needed(self) -> None:
        while len(self._data) > self._max_items:
            self._data.popitem(last=False)

    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            now = time.monotonic()
            self._purge_expired(now)
            item = self._data.get(key)
            if item is None:
                return None
            value, exp = item
            if exp is not None and exp <= now:
                self._data.pop(key, None)
                return None
            self._data.move_to_end(key, last=True)
            return value

    async def set(self, key: str, value: str, ttl: Optional[int]) -> None:
        async with self._lock:
            now = time.monotonic()
            exp = (now + ttl) if ttl is not None else None
            self._data[key] = (value, exp)
            self._data.move_to_end(key, last=True)
            self._purge_expired(now)
            self._evict_if_needed()

    async def add(self, key: str, value: str, ttl: Optional[int]) -> bool:
        async with self._lock:
            now = time.monotonic()
            self._purge_expired(now)
            if key in self._data:
                _, exp = self._data[key]
                if exp is None or exp > now:
                    return False
                self._data.pop(key, None)
            exp = (now + ttl) if ttl is not None else None
            self._data[key] = (value, exp)
            self._data.move_to_end(key, last=True)
            self._evict_if_needed()
            return True

    async def delete(self, key: str) -> bool:
        async with self._lock:
            existed = key in self._data
            self._data.pop(key, None)
            return existed

    async def exists(self, key: str) -> bool:
        async with self._lock:
            now = time.monotonic()
            self._purge_expired(now)
            item = self._data.get(key)
            if item is None:
                return False
            _, exp = item
            if exp is not None and exp <= now:
                self._data.pop(key, None)
                return False
            return True

    async def incrby(self, key: str, amount: int) -> int:
        async with self._lock:
            now = time.monotonic()
            self._purge_expired(now)
            item = self._data.get(key)
            if item is None:
                new_val = amount
                self._data[key] = (str(new_val), None)
                self._data.move_to_end(key, last=True)
                self._evict_if_needed()
                return new_val
            raw, exp = item
            try:
                current = int(raw)
            except Exception:
                current = 0
            new_val = current + amount
            self._data[key] = (str(new_val), exp)
            self._data.move_to_end(key, last=True)
            return new_val

    async def expire(self, key: str, seconds: int) -> bool:
        async with self._lock:
            now = time.monotonic()
            self._purge_expired(now)
            item = self._data.get(key)
            if item is None:
                return False
            value, _ = item
            self._data[key] = (value, now + seconds)
            self._data.move_to_end(key, last=True)
            return True

    async def ttl(self, key: str) -> int:
        async with self._lock:
            now = time.monotonic()
            self._purge_expired(now)
            item = self._data.get(key)
            if item is None:
                return -2
            _, exp = item
            if exp is None:
                return -1
            remaining = int(exp - now)
            if remaining <= 0:
                self._data.pop(key, None)
                return -2
            return remaining

    async def close(self) -> None:
        return


class CacheClient:
    """Async cache client with JSON serialization and Redis to memory fallback."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        *,
        in_memory_max_items: int = 2048,
    ) -> None:
        self.settings = settings or get_settings()
        self._redis: Optional[redis.Redis] = None
        self._redis_lock = asyncio.Lock()
        self._redis_disabled = False
        self._memory = _InMemoryLRUTTLCache(max_items=in_memory_max_items)

    async def _get_redis(self) -> Optional[redis.Redis]:
        """Return a connected Redis client, or None (fallback mode)."""
        if self._redis_disabled:
            return None
        if not self.settings.redis_url:
            return None
        if self._redis is not None:
            return self._redis

        async with self._redis_lock:
            if self._redis_disabled:
                return None
            if self._redis is not None:
                return self._redis
            try:
                r = redis.from_url(
                    self.settings.redis_url,
                    password=self.settings.redis_password,
                    decode_responses=True,
                )
                await r.ping()
                self._redis = r
                logger.debug("Redis connection established")
            except Exception as e:
                self._redis_disabled = True
                self._redis = None
                logger.warning(
                    "Redis unavailable; using in-memory cache fallback",
                    error=str(e),
                )
                return None

        return self._redis

    def _make_key(self, key: str, namespace: Optional[str] = None) -> str:
        """Create namespaced key."""
        if namespace:
            return f"{namespace}:{key}"
        return key

    async def get(
        self,
        key: str,
        namespace: Optional[str] = None,
        default: Optional[T] = None,
    ) -> Optional[T]:
        """Get value from cache."""
        full_key = self._make_key(key, namespace)

        try:
            r = await self._get_redis()
            if r is None:
                value = await self._memory.get(full_key)
            else:
                try:
                    value = await r.get(full_key)
                except Exception as e:
                    logger.warning(
                        "Redis get failed; using in-memory fallback",
                        key=full_key,
                        error=str(e),
                    )
                    self._redis_disabled = True
                    value = await self._memory.get(full_key)

            if value is None:
                return default

            try:
                return cast(T, json.loads(value))
            except json.JSONDecodeError:
                return cast(T, value)
        except Exception as e:
            logger.error("Cache get failed", key=full_key, error=str(e))
            return default

    async def set(
        self,
        key: str,
        value: Any,
        namespace: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set value in cache."""
        full_key = self._make_key(key, namespace)

        try:
            if not isinstance(value, str):
                value = json.dumps(value)

            r = await self._get_redis()
            if r is None:
                await self._memory.set(full_key, value, ttl)
                logger.debug("Cache set", key=full_key, ttl=ttl, backend="memory")
                return True

            try:
                await r.set(full_key, value, ex=ttl)
                logger.debug("Cache set", key=full_key, ttl=ttl, backend="redis")
                return True
            except Exception as e:
                logger.warning(
                    "Redis set failed; using in-memory fallback",
                    key=full_key,
                    error=str(e),
                )
                self._redis_disabled = True
                await self._memory.set(full_key, value, ttl)
                return True
        except Exception as e:
            logger.error("Cache set failed", key=full_key, error=str(e))
            return False

    async def delete(self, key: str, namespace: Optional[str] = None) -> bool:
        """Delete key from cache."""
        full_key = self._make_key(key, namespace)

        try:
            r = await self._get_redis()
            if r is None:
                deleted = await self._memory.delete(full_key)
                return deleted

            try:
                result = await r.delete(full_key)
                return result > 0
            except Exception as e:
                logger.warning(
                    "Redis delete failed; using in-memory fallback",
                    key=full_key,
                    error=str(e),
                )
                self._redis_disabled = True
                return await self._memory.delete(full_key)
        except Exception as e:
            logger.error("Cache delete failed", key=full_key, error=str(e))
            return False

    async def increment(
        self,
        key: str,
        amount: int = 1,
        namespace: Optional[str] = None,
    ) -> int:
        """Increment counter in cache."""
        full_key = self._make_key(key, namespace)

        try:
            r = await self._get_redis()
            if r is None:
                value = await self._memory.incrby(full_key, amount)
                return value

            try:
                value = await r.incrby(full_key, amount)
                return value
            except Exception as e:
                logger.warning(
                    "Redis increment failed; using in-memory fallback",
                    key=full_key,
                    error=str(e),
                )
                self._redis_disabled = True
                return await self._memory.incrby(full_key, amount)
        except Exception as e:
            logger.error("Cache increment failed", key=full_key, error=str(e))
            return 0

    async def close(self) -> None:
        """Close cache backend connections (best-effort)."""
        if self._redis:
            try:
                await self._redis.close()
            except Exception as e:
                logger.debug("Redis connection close failed (ignored)", error=str(e))
            finally:
                self._redis = None
        await self._memory.close()
        logger.debug("Cache client closed", redis_disabled=self._redis_disabled)

    async def __aenter__(self) -> "CacheClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

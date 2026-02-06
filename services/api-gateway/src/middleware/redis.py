"""Redis client singleton for caching and rate limiting.

Provides a unified cache layer that falls back to in-memory dict
when Redis is unavailable (local development / no Memorystore).
"""

import json
import os
import time
from typing import Any, Optional

from ..logging import get_logger

logger = get_logger(__name__)

# Try to import redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis package not installed, using in-memory fallback")

# Global Redis client - initialized in main.py lifespan
redis_client: Optional[Any] = None

# In-memory fallback cache
_memory_cache: dict[str, tuple[float, str]] = {}  # key -> (expire_timestamp, json_value)
_MAX_MEMORY_ENTRIES = 500


def get_redis_client() -> Optional[Any]:
    """Get the Redis client instance."""
    return redis_client


def set_redis_client(client: Any) -> None:
    """Set the Redis client instance."""
    global redis_client
    redis_client = client


async def init_redis() -> bool:
    """Initialize Redis connection from environment.

    Returns True if Redis connected, False if falling back to memory.
    """
    global redis_client

    redis_url = os.getenv("REDIS_URL") or os.getenv("REDISHOST")
    if not redis_url and not REDIS_AVAILABLE:
        logger.info("Redis not configured, using in-memory cache")
        return False

    if not REDIS_AVAILABLE:
        logger.info("redis package not available, using in-memory cache")
        return False

    try:
        # Support full URL (redis://host:port) or just host
        if redis_url and redis_url.startswith("redis://"):
            redis_client = redis.from_url(redis_url, decode_responses=True)
        else:
            host = redis_url or os.getenv("REDISHOST", "localhost")
            port = int(os.getenv("REDISPORT", "6379"))
            redis_client = redis.Redis(
                host=host,
                port=port,
                db=0,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=2,
                retry_on_timeout=True,
            )

        # Test connection
        redis_client.ping()
        logger.info("Redis connected", host=redis_url or "localhost")
        return True

    except Exception as e:
        logger.warning("Redis connection failed, using in-memory cache", error=str(e))
        redis_client = None
        return False


async def close_redis() -> None:
    """Close Redis connection."""
    global redis_client
    if redis_client:
        try:
            redis_client.close()
        except Exception:
            pass
        redis_client = None


def cache_get(key: str) -> Optional[Any]:
    """Get a value from cache (Redis or in-memory fallback).

    Returns deserialized value or None if not found/expired.
    """
    # Try Redis first
    if redis_client:
        try:
            value = redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.debug("Redis GET failed, trying memory", error=str(e))

    # Fallback to in-memory
    if key in _memory_cache:
        expire_ts, json_value = _memory_cache[key]
        if time.time() < expire_ts:
            return json.loads(json_value)
        else:
            del _memory_cache[key]

    return None


def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    """Set a value in cache with TTL in seconds.

    Args:
        key: Cache key
        value: Value to cache (must be JSON-serializable)
        ttl: Time-to-live in seconds (default: 60)
    """
    json_value = json.dumps(value, default=str)

    # Try Redis
    if redis_client:
        try:
            redis_client.setex(key, ttl, json_value)
            return
        except Exception as e:
            logger.debug("Redis SET failed, using memory", error=str(e))

    # Fallback to in-memory
    _memory_cache[key] = (time.time() + ttl, json_value)

    # Evict oldest entries if over limit
    if len(_memory_cache) > _MAX_MEMORY_ENTRIES:
        sorted_keys = sorted(_memory_cache.keys(), key=lambda k: _memory_cache[k][0])
        for old_key in sorted_keys[:len(_memory_cache) - _MAX_MEMORY_ENTRIES]:
            del _memory_cache[old_key]


def cache_delete(key: str) -> None:
    """Delete a key from cache."""
    if redis_client:
        try:
            redis_client.delete(key)
        except Exception:
            pass

    _memory_cache.pop(key, None)


def cache_info() -> dict:
    """Get cache status info."""
    info = {
        "backend": "redis" if redis_client else "memory",
        "memory_entries": len(_memory_cache),
    }

    if redis_client:
        try:
            redis_info = redis_client.info("memory")
            info["redis_used_memory"] = redis_info.get("used_memory_human", "unknown")
            info["redis_keys"] = redis_client.dbsize()
        except Exception:
            info["redis_status"] = "error"

    return info

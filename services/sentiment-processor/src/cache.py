"""Sentiment result caching utilities.

This module provides caching functionality for sentiment analysis results
to reduce API costs and improve response times.
Uses Firestore for distributed caching with in-memory fallback.
"""

import hashlib
from typing import Any

from sentilyze_core import FirestoreCacheClient, SentimentResult, get_logger, get_settings

from .config import MarketType

logger = get_logger(__name__)
settings = get_settings()


class SentimentCache:
    """Cache for sentiment analysis results using Firestore.
    
    This class provides methods to cache and retrieve sentiment results
    based on content hash and market type to reduce duplicate API calls.
    Uses Firestore as primary cache with automatic fallback.
    """

    def __init__(self, cache_client: FirestoreCacheClient | None = None) -> None:
        """Initialize the sentiment cache.

        Args:
            cache_client: Optional FirestoreCacheClient instance. Creates new if None.
        """
        self.cache = cache_client or FirestoreCacheClient()
        self._namespace = "sentiment"

    # Note: sentilyze_core.MarketType does not have a GENERIC value. We default to CRYPTO.
    def get_cache_key(self, content: str, market_type: MarketType = MarketType.CRYPTO) -> str:
        """Generate a cache key for content.

        The key is based on a hash of the first 200 characters of content
        combined with the market type to ensure market-specific caching.

        Args:
            content: Text content to hash
            market_type: Market type for the analysis

        Returns:
            Cache key string
        """
        content_prefix = (content or "")[:200]
        content_hash = hashlib.sha256(content_prefix.encode()).hexdigest()[:16]
        return f"{market_type.value}:{content_hash}"

    async def get_cached_result(
        self,
        cache_key: str,
    ) -> dict[str, Any] | None:
        """Retrieve a cached sentiment result.

        Args:
            cache_key: The cache key to look up

        Returns:
            Cached result dict or None if not found/error
        """
        try:
            result = await self.cache.get(cache_key, namespace=self._namespace)
            if result:
                logger.debug(f"Cache hit for key: {cache_key}")
                return result
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")
        return None

    async def cache_result(
        self,
        cache_key: str,
        sentiment: SentimentResult,
        ttl: int | None = None,
    ) -> bool:
        """Cache a sentiment result.

        Args:
            cache_key: The cache key to store under
            sentiment: SentimentResult to cache
            ttl: Time-to-live in seconds (uses default if None)

        Returns:
            True if cached successfully, False otherwise
        """
        try:
            ttl_seconds = ttl or settings.sentiment_cache_ttl
            await self.cache.set(
                cache_key,
                sentiment.model_dump(mode="json"),
                namespace=self._namespace,
                ttl=ttl_seconds,
            )
            logger.debug(f"Cached result for key: {cache_key}, ttl={ttl_seconds}s")
            return True
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")
            return False

    async def exists(self, cache_key: str) -> bool:
        """Check if a cache key exists.

        Args:
            cache_key: The cache key to check

        Returns:
            True if key exists, False otherwise
        """
        try:
            result = await self.cache.get(cache_key, namespace=self._namespace)
            return result is not None
        except Exception as e:
            logger.warning(f"Cache exists check failed: {e}")
            return False

    async def add(
        self,
        cache_key: str,
        value: Any,
        ttl: int | None = None,
        namespace: str | None = None,
    ) -> bool:
        """Atomic set-if-not-exists operation (for deduplication/locking).

        Args:
            cache_key: The cache key to add
            value: Value to store
            ttl: Time-to-live in seconds (uses default if None)
            namespace: Optional namespace override (uses self._namespace if None)

        Returns:
            True if key was set (didn't exist), False if key already exists
        """
        try:
            ttl_seconds = ttl or settings.sentiment_cache_ttl
            ns = namespace or self._namespace
            return await self.cache.add(cache_key, value, ttl=ttl_seconds, namespace=ns)
        except Exception as e:
            logger.warning(f"Cache add failed: {e}")
            return False

    async def set(
        self,
        cache_key: str,
        value: Any,
        ttl: int | None = None,
        namespace: str | None = None,
    ) -> bool:
        """Set a cache value (generic interface for compatibility).

        Args:
            cache_key: The cache key to store under
            value: Value to store
            ttl: Time-to-live in seconds (uses default if None)
            namespace: Optional namespace override (uses self._namespace if None)

        Returns:
            True if cached successfully, False otherwise
        """
        try:
            ttl_seconds = ttl or settings.sentiment_cache_ttl
            ns = namespace or self._namespace
            await self.cache.set(cache_key, value, ttl=ttl_seconds, namespace=ns)
            logger.debug(f"Set cache for key: {cache_key}, ttl={ttl_seconds}s, namespace={ns}")
            return True
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")
            return False

    async def delete(self, cache_key: str, namespace: str | None = None) -> bool:
        """Delete a cached result.

        Args:
            cache_key: The cache key to delete
            namespace: Optional namespace override (uses self._namespace if None)

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            ns = namespace or self._namespace
            await self.cache.delete(cache_key, namespace=ns)
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed: {e}")
            return False

    async def clear_market_cache(self, market_type: MarketType) -> int:
        """Clear all cached results for a specific market type.
        
        Note: Firestore doesn't support pattern-based deletion efficiently.
        This is a best-effort implementation.

        Args:
            market_type: Market type to clear cache for

        Returns:
            Number of keys cleared (always 0 for Firestore - requires manual cleanup)
        """
        logger.warning(
            f"Clearing market cache not supported with Firestore. "
            f"Use Firestore TTL or manual cleanup for {market_type.value}"
        )
        return 0

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.
        
        Note: Firestore doesn't support key enumeration efficiently.
        Returns basic info only.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "backend": "firestore",
            "namespace": self._namespace,
            "note": "Firestore doesn't support key enumeration",
        }

    async def close(self) -> None:
        """Close cache connection."""
        await self.cache.close()
        logger.info("Sentiment cache closed")


class TieredCache:
    """Tiered caching with in-memory and Firestore layers.
    
    Provides faster lookups for frequently accessed items while
    maintaining persistence through Firestore.
    """

    def __init__(
        self,
        firestore_cache: FirestoreCacheClient | None = None,
        max_memory_items: int = 1000,
    ) -> None:
        self.memory_cache: dict[str, dict[str, Any]] = {}
        self.firestore_cache = firestore_cache or FirestoreCacheClient()
        self.max_memory_items = max_memory_items
        self._namespace = "sentiment"

    async def get(self, cache_key: str) -> dict[str, Any] | None:
        """Get cached result from memory or Firestore."""
        # Check memory first
        if cache_key in self.memory_cache:
            logger.debug(f"Memory cache hit: {cache_key}")
            return self.memory_cache[cache_key]

        # Fall back to Firestore
        try:
            result = await self.firestore_cache.get(cache_key, namespace=self._namespace)
            if result:
                # Add to memory cache
                self._add_to_memory(cache_key, result)
            return result
        except Exception as e:
            logger.warning(f"Firestore cache get failed: {e}")
            return None

    async def set(
        self,
        cache_key: str,
        value: dict[str, Any],
        ttl: int | None = None,
    ) -> bool:
        """Set cached result in both memory and Firestore."""
        # Add to memory
        self._add_to_memory(cache_key, value)

        # Add to Firestore
        try:
            ttl_seconds = ttl or settings.sentiment_cache_ttl
            await self.firestore_cache.set(
                cache_key,
                value,
                namespace=self._namespace,
                ttl=ttl_seconds,
            )
            return True
        except Exception as e:
            logger.warning(f"Firestore cache set failed: {e}")
            return False

    def _add_to_memory(self, cache_key: str, value: dict[str, Any]) -> None:
        """Add an item to memory cache with LRU eviction."""
        # Simple LRU: if at capacity, clear half the cache
        if len(self.memory_cache) >= self.max_memory_items:
            keys_to_remove = list(self.memory_cache.keys())[: self.max_memory_items // 2]
            for key in keys_to_remove:
                del self.memory_cache[key]
            logger.debug(f"Evicted {len(keys_to_remove)} items from memory cache")

        self.memory_cache[cache_key] = value

    async def close(self) -> None:
        """Close cache connections."""
        self.memory_cache.clear()
        await self.firestore_cache.close()

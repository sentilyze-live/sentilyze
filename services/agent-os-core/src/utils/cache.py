"""BigQuery caching layer for cost optimization."""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from functools import wraps

import structlog
from google.cloud import firestore

from src.config import settings

logger = structlog.get_logger(__name__)


class BigQueryCache:
    """Cache layer for BigQuery queries to reduce costs."""
    
    def __init__(self, ttl_minutes: int = None):
        """Initialize cache.
        
        Args:
            ttl_minutes: Cache time-to-live in minutes
        """
        self.ttl_minutes = ttl_minutes or settings.BIGQUERY_CACHE_TTL_MINUTES
        self.firestore_client = None
        self._local_cache: Dict[str, Dict[str, Any]] = {}
        
        if settings.CACHE_TYPE == "firestore":
            try:
                self.firestore_client = firestore.Client(project=settings.FIRESTORE_PROJECT_ID)
                logger.info("bigquery_cache.firestore_initialized")
            except Exception as e:
                logger.warning("bigquery_cache.firestore_failed", error=str(e))
    
    def _generate_key(self, query: str, params: Dict[str, Any]) -> str:
        """Generate cache key from query and parameters.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Cache key string
        """
        key_data = f"{query}:{json.dumps(params, sort_keys=True, default=str)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_cache_valid(self, cached_at: datetime) -> bool:
        """Check if cache entry is still valid.
        
        Args:
            cached_at: When the cache was created
            
        Returns:
            True if cache is still valid
        """
        if not settings.ENABLE_BIGQUERY_CACHE:
            return False
            
        expiry_time = cached_at + timedelta(minutes=self.ttl_minutes)
        return datetime.utcnow() < expiry_time
    
    async def get(self, query: str, params: Dict[str, Any] = None) -> Optional[Any]:
        """Get cached result if available and valid.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Cached data or None
        """
        if not settings.ENABLE_BIGQUERY_CACHE:
            return None
            
        cache_key = self._generate_key(query, params or {})
        
        # Check local cache first (faster)
        if cache_key in self._local_cache:
            cached = self._local_cache[cache_key]
            if self._is_cache_valid(cached["cached_at"]):
                logger.debug("bigquery_cache.local_hit", key=cache_key[:8])
                return cached["data"]
            else:
                del self._local_cache[cache_key]
        
        # Check Firestore cache
        if self.firestore_client:
            try:
                doc_ref = self.firestore_client.collection("bigquery_cache").document(cache_key)
                doc = doc_ref.get()
                
                if doc.exists:
                    data = doc.to_dict()
                    cached_at = data.get("cached_at")
                    
                    if isinstance(cached_at, str):
                        cached_at = datetime.fromisoformat(cached_at)
                    
                    if self._is_cache_valid(cached_at):
                        logger.info("bigquery_cache.firestore_hit", key=cache_key[:8])
                        # Update local cache
                        self._local_cache[cache_key] = {
                            "data": data["result"],
                            "cached_at": cached_at
                        }
                        return data["result"]
                    else:
                        # Delete expired cache
                        doc_ref.delete()
                        
            except Exception as e:
                logger.warning("bigquery_cache.firestore_error", error=str(e))
        
        return None
    
    async def set(self, query: str, params: Dict[str, Any], data: Any) -> None:
        """Cache query result.
        
        Args:
            query: SQL query string
            params: Query parameters
            data: Result data to cache
        """
        if not settings.ENABLE_BIGQUERY_CACHE:
            return
            
        cache_key = self._generate_key(query, params or {})
        cached_at = datetime.utcnow()
        
        # Update local cache
        self._local_cache[cache_key] = {
            "data": data,
            "cached_at": cached_at
        }
        
        # Update Firestore cache
        if self.firestore_client:
            try:
                doc_ref = self.firestore_client.collection("bigquery_cache").document(cache_key)
                doc_ref.set({
                    "query_hash": cache_key,
                    "result": data,
                    "cached_at": cached_at.isoformat(),
                    "ttl_minutes": self.ttl_minutes,
                    "expires_at": (cached_at + timedelta(minutes=self.ttl_minutes)).isoformat()
                })
                logger.debug("bigquery_cache.stored", key=cache_key[:8])
            except Exception as e:
                logger.warning("bigquery_cache.store_error", error=str(e))
    
    async def clear_expired(self) -> int:
        """Clear expired cache entries.
        
        Returns:
            Number of entries cleared
        """
        cleared = 0
        
        # Clear local cache
        now = datetime.utcnow()
        expired_keys = [
            key for key, cached in self._local_cache.items()
            if now > cached["cached_at"] + timedelta(minutes=self.ttl_minutes)
        ]
        for key in expired_keys:
            del self._local_cache[key]
            cleared += 1
        
        # Clear Firestore cache
        if self.firestore_client:
            try:
                now_str = now.isoformat()
                docs = self.firestore_client.collection("bigquery_cache") \
                    .where("expires_at", "<", now_str) \
                    .limit(100) \
                    .stream()
                
                for doc in docs:
                    doc.reference.delete()
                    cleared += 1
                    
                logger.info("bigquery_cache.cleared_expired", count=cleared)
            except Exception as e:
                logger.warning("bigquery_cache.clear_error", error=str(e))
        
        return cleared
    
    def cached_query(self, ttl_minutes: int = None):
        """Decorator for caching BigQuery queries.
        
        Args:
            ttl_minutes: Override default TTL
            
        Returns:
            Decorator function
        """
        cache = BigQueryCache(ttl_minutes or self.ttl_minutes)
        
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Skip cache if explicitly disabled
                if not settings.ENABLE_BIGQUERY_CACHE:
                    return await func(*args, **kwargs)
                
                # Generate cache key from function args
                query_params = {
                    "func": func.__name__,
                    "args": args[1:],  # Skip self
                    "kwargs": kwargs
                }
                
                # Try to get from cache
                cached_result = await cache.get("", query_params)
                if cached_result is not None:
                    return cached_result
                
                # Execute query
                result = await func(*args, **kwargs)
                
                # Cache result
                await cache.set("", query_params, result)
                
                return result
            
            return wrapper
        return decorator


# Global cache instance
bigquery_cache = BigQueryCache()

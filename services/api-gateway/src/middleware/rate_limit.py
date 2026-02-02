"""Rate limiting middleware with Firestore-based storage."""

import time
from typing import Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from ..config import get_settings
from ..logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class MemoryRateLimiter:
    """In-memory rate limiter as fallback when Firestore unavailable."""
    
    def __init__(self) -> None:
        self._storage: dict[str, tuple[int, float]] = {}
        self.requests = settings.rate_limit_requests
        self.window = settings.rate_limit_window
    
    def _get_key(self, identifier: str) -> str:
        """Generate rate limit key."""
        return f"rate_limit:{identifier}"
    
    def _clean_expired(self) -> None:
        """Clean expired entries."""
        now = time.time()
        expired = [
            key for key, (_, expiry) in self._storage.items()
            if expiry < now
        ]
        for key in expired:
            del self._storage[key]
    
    async def is_allowed(self, identifier: str) -> tuple[bool, int]:
        """Check if request is allowed under rate limit.
        
        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            
        Returns:
            Tuple of (allowed, remaining_requests)
        """
        self._clean_expired()
        
        key = self._get_key(identifier)
        now = time.time()
        
        if key not in self._storage:
            # First request
            self._storage[key] = (1, now + self.window)
            return True, self.requests - 1
        
        count, expiry = self._storage[key]
        
        if now > expiry:
            # Window expired, reset
            self._storage[key] = (1, now + self.window)
            return True, self.requests - 1
        
        if count >= self.requests:
            # Rate limit exceeded
            return False, 0
        
        # Increment counter
        self._storage[key] = (count + 1, expiry)
        remaining = self.requests - count - 1
        
        return True, max(0, remaining)
    
    async def get_retry_after(self, identifier: str) -> int:
        """Get seconds until rate limit resets."""
        key = self._get_key(identifier)
        if key in self._storage:
            _, expiry = self._storage[key]
            return max(0, int(expiry - time.time()))
        return 0


class FirestoreRateLimiter:
    """Firestore-based rate limiter for distributed systems."""
    
    def __init__(self) -> None:
        self.requests = settings.rate_limit_requests
        self.window = settings.rate_limit_window
        self._cache: Optional[object] = None
    
    @property
    async def cache(self) -> object:
        """Lazy load Firestore cache client."""
        if self._cache is None:
            try:
                from sentilyze_core import FirestoreCacheClient
                self._cache = FirestoreCacheClient()
            except Exception as e:
                logger.error("Failed to initialize Firestore cache", error=str(e))
                raise
        return self._cache
    
    def _get_key(self, identifier: str) -> str:
        """Generate rate limit key."""
        return f"rate_limit:{identifier}"
    
    async def is_allowed(self, identifier: str) -> tuple[bool, int]:
        """Check if request is allowed under rate limit."""
        key = self._get_key(identifier)
        
        try:
            cache = await self.cache
            current = await cache.get(key, namespace="rate_limit")
            
            if current is None:
                # First request - set counter with TTL
                await cache.set(key, 1, ttl=self.window, namespace="rate_limit")
                return True, self.requests - 1
            
            count = int(current)
            
            if count >= self.requests:
                return False, 0
            
            # Increment counter
            await cache.increment(key, 1, namespace="rate_limit")
            remaining = self.requests - count - 1
            
            return True, max(0, remaining)
            
        except Exception as e:
            logger.error("Firestore rate limit check failed", error=str(e))
            # Fallback to memory limiter
            return await memory_limiter.is_allowed(identifier)
    
    async def get_retry_after(self, identifier: str) -> int:
        """Get seconds until rate limit resets."""
        key = self._get_key(identifier)
        
        try:
            cache = await self.cache
            ttl = await cache.ttl(key, namespace="rate_limit")
            return max(0, ttl)
        except Exception:
            return await memory_limiter.get_retry_after(identifier)


# Global limiter instances
memory_limiter = MemoryRateLimiter()
firestore_limiter: Optional[FirestoreRateLimiter] = None


def get_rate_limiter() -> FirestoreRateLimiter | MemoryRateLimiter:
    """Get appropriate rate limiter.
    
    Returns:
        Firestore limiter if available, otherwise memory limiter
    """
    global firestore_limiter
    
    if not settings.rate_limit_enabled:
        return memory_limiter
    
    if firestore_limiter is None:
        try:
            firestore_limiter = FirestoreRateLimiter()
        except Exception:
            logger.warning("Firestore rate limiter unavailable, using memory fallback")
            return memory_limiter
    
    return firestore_limiter


async def rate_limit_middleware(request: Request, call_next):
    """FastAPI middleware for rate limiting.
    
    Args:
        request: FastAPI request
        call_next: Next middleware/handler
        
    Returns:
        Response
    """
    if not settings.rate_limit_enabled:
        return await call_next(request)
    
    # Get client identifier (prefer user ID from token if available)
    identifier = request.client.host if request.client else "unknown"
    
    # Try to get user ID from Authorization header for better rate limiting
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # Extract user ID from token if possible (simplified)
        # In production, decode JWT to get user ID
    
    limiter = get_rate_limiter()
    allowed, remaining = await limiter.is_allowed(identifier)
    
    if not allowed:
        retry_after = await limiter.get_retry_after(identifier)
        logger.warning(
            "Rate limit exceeded",
            identifier=identifier,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "Rate limit exceeded",
                "retry_after": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers
    response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_requests)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    
    return response


async def check_rate_limit(
    request: Request,
    limit: Optional[int] = None,
    window: Optional[int] = None,
) -> None:
    """Dependency for route-specific rate limiting.
    
    Args:
        request: FastAPI request
        limit: Custom limit (defaults to settings)
        window: Custom window (defaults to settings)
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    if not settings.rate_limit_enabled:
        return
    
    identifier = request.client.host if request.client else "unknown"
    
    # Use custom or default limits
    req_limit = limit or settings.rate_limit_requests
    req_window = window or settings.rate_limit_window
    
    limiter = get_rate_limiter()
    allowed, _ = await limiter.is_allowed(f"{identifier}:{request.url.path}")
    
    if not allowed:
        retry_after = await limiter.get_retry_after(f"{identifier}:{request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry after {retry_after} seconds",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(req_limit),
                "X-RateLimit-Remaining": "0",
            },
        )


async def close_rate_limiter() -> None:
    """Close rate limiter connections on shutdown."""
    global firestore_limiter
    if firestore_limiter and firestore_limiter._cache:
        try:
            await firestore_limiter._cache.close()
        except Exception as e:
            logger.error("Error closing rate limiter cache", error=str(e))

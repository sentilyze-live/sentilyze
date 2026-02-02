"""Circuit breaker pattern implementation for external API calls.

This module provides a circuit breaker to prevent cascading failures
when external services (GoldAPI, Finnhub, Binance, etc.) are down.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Service is down, requests fail fast
- HALF_OPEN: Testing if service is back up
"""

import asyncio
import time
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from .logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker for external service calls.
    
    Example:
        breaker = CircuitBreaker(name="goldapi", fail_max=5, reset_timeout=60)
        
        @breaker
        async def fetch_price():
            return await api.get_price()
    """
    
    def __init__(
        self,
        name: str,
        fail_max: int = 5,
        reset_timeout: int = 60,
        half_open_max: int = 3,
        expected_exception: type = Exception,
    ):
        """Initialize circuit breaker.
        
        Args:
            name: Circuit breaker name (for logging)
            fail_max: Failures before opening circuit
            reset_timeout: Seconds before trying half-open
            half_open_max: Max calls in half-open state
            expected_exception: Exception type to count as failure
        """
        self.name = name
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self.half_open_max = half_open_max
        self.expected_exception = expected_exception
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state
    
    async def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Call function with circuit breaker protection."""
        async with self._lock:
            # Check if we should transition from OPEN to HALF_OPEN
            if self._state == CircuitState.OPEN:
                if self._last_failure_time and \
                   time.time() - self._last_failure_time >= self.reset_timeout:
                    logger.info(
                        f"Circuit breaker {self.name} entering half-open state",
                        timeout=self.reset_timeout,
                    )
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                else:
                    raise CircuitBreakerOpen(
                        f"Circuit breaker {self.name} is OPEN"
                    )
            
            # In HALF_OPEN state, limit concurrent calls
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max:
                    raise CircuitBreakerOpen(
                        f"Circuit breaker {self.name} half-open limit reached"
                    )
                self._half_open_calls += 1
        
        # Call the function (outside lock to allow concurrency)
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except self.expected_exception as e:
            await self._on_failure()
            raise
    
    async def _on_success(self) -> None:
        """Handle successful call."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                # If enough successes, close the circuit
                if self._success_count >= self.half_open_max:
                    logger.info(
                        f"Circuit breaker {self.name} closed after recovery",
                        successes=self._success_count,
                    )
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
            else:
                # In CLOSED state, reset failure count on success
                if self._failure_count > 0:
                    self._failure_count = 0
    
    async def _on_failure(self) -> None:
        """Handle failed call."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                # Back to OPEN if fails in half-open
                logger.warning(
                    f"Circuit breaker {self.name} back to OPEN after half-open failure",
                    failure_count=self._failure_count,
                )
                self._state = CircuitState.OPEN
                self._half_open_calls = 0
            elif self._state == CircuitState.CLOSED and \
                 self._failure_count >= self.fail_max:
                # Open circuit after max failures
                logger.error(
                    f"Circuit breaker {self.name} OPENED after {self.fail_max} failures",
                    failures=self._failure_count,
                )
                self._state = CircuitState.OPEN
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to wrap function with circuit breaker."""
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await self.call(func, *args, **kwargs)
        
        # Attach circuit breaker to function for manual control
        wrapper._circuit_breaker = self
        return wrapper


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""
    pass


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    name: Optional[str] = None,
    expected_exception: type = Exception,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator factory for circuit breaker protection.

    This is a small compatibility wrapper used by some ingestion collectors:
      @circuit_breaker(failure_threshold=5, recovery_timeout=60)
      async def call_api(...): ...

    Args:
        failure_threshold: Failures before opening circuit (maps to fail_max)
        recovery_timeout: Seconds before trying half-open (maps to reset_timeout)
        name: Optional breaker name (defaults to function name)
        expected_exception: Exception type to count as failure
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        breaker = CircuitBreaker(
            name=name or getattr(func, "__name__", "circuit_breaker"),
            fail_max=failure_threshold,
            reset_timeout=recovery_timeout,
            expected_exception=expected_exception,
        )

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await breaker.call(func, *args, **kwargs)

        # Attach for introspection/testing
        wrapper._circuit_breaker = breaker
        return wrapper

    return decorator


# Pre-configured circuit breakers for external services
goldapi_circuit = CircuitBreaker(
    name="goldapi",
    fail_max=5,
    reset_timeout=60,
    half_open_max=3,
)

finnhub_circuit = CircuitBreaker(
    name="finnhub",
    fail_max=5,
    reset_timeout=60,
    half_open_max=3,
)

alphavantage_circuit = CircuitBreaker(
    name="alphavantage",
    fail_max=3,
    reset_timeout=120,
    half_open_max=2,
)

cryptoapi_circuit = CircuitBreaker(
    name="cryptoapi",
    fail_max=5,
    reset_timeout=60,
    half_open_max=3,
)

binance_circuit = CircuitBreaker(
    name="binance",
    fail_max=5,
    reset_timeout=30,
    half_open_max=3,
)

coingecko_circuit = CircuitBreaker(
    name="coingecko",
    fail_max=5,
    reset_timeout=60,
    half_open_max=3,
)

"""Custom exceptions for Sentilyze services."""

from typing import Any, Optional


class SentilyzeError(Exception):
    """Base exception for all Sentilyze errors."""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or "UNKNOWN_ERROR"
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"[{self.code}] {self.message} - Details: {self.details}"
        return f"[{self.code}] {self.message}"


class ConfigurationError(SentilyzeError):
    """Configuration-related errors."""

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code="CONFIG_ERROR", details=details)


class ValidationError(SentilyzeError):
    """Data validation errors."""

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code="VALIDATION_ERROR", details=details)


class PubSubError(SentilyzeError):
    """Pub/Sub messaging errors."""

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code="PUBSUB_ERROR", details=details)


class BigQueryError(SentilyzeError):
    """BigQuery database errors."""

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code="BIGQUERY_ERROR", details=details)


class CacheError(SentilyzeError):
    """Cache (Redis/Firestore) errors."""

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code="CACHE_ERROR", details=details)


class AuthenticationError(SentilyzeError):
    """Authentication errors."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code="AUTH_ERROR", details=details)


class AuthorizationError(SentilyzeError):
    """Authorization/permission errors."""

    def __init__(
        self,
        message: str = "Permission denied",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code="FORBIDDEN", details=details)


class RateLimitError(SentilyzeError):
    """Rate limiting errors."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code="RATE_LIMIT", details=details)
        self.retry_after = retry_after


class ExternalServiceError(SentilyzeError):
    """External API/service errors."""

    def __init__(
        self,
        message: str,
        service: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code="EXTERNAL_SERVICE_ERROR", details=details)
        self.service = service


class NotFoundError(SentilyzeError):
    """Resource not found errors."""

    def __init__(
        self,
        resource: str,
        identifier: Optional[str] = None,
    ) -> None:
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} '{identifier}' not found"
        super().__init__(message, code="NOT_FOUND", details={"resource": resource, "id": identifier})


class MarketDataError(SentilyzeError):
    """Market data specific errors."""
    
    def __init__(
        self,
        message: str,
        symbol: Optional[str] = None,
        market_type: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code="MARKET_DATA_ERROR", details=details)
        self.symbol = symbol
        self.market_type = market_type


class CircuitBreakerOpen(SentilyzeError):
    """Circuit breaker is open."""
    
    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
    ) -> None:
        super().__init__(message, code="CIRCUIT_OPEN", details={"service": service})
        self.service = service

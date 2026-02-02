"""Logging utilities for API Gateway."""

import logging
import sys
from typing import Any, Optional

from .config import get_settings

settings = get_settings()

# SENSITIVE_PATTERNS for PII redaction
SENSITIVE_PATTERNS = [
    (r'"password"\s*:\s*"[^"]*"', '"password": "***"'),
    (r'"api_key"\s*:\s*"[^"]*"', '"api_key": "***"'),
    (r'"token"\s*:\s*"[^"]*"', '"token": "***"'),
    (r'Bearer\s+[^\s"\']+', 'Bearer ***'),
    (r'X-API-Key:\s*[^\s"\']+', 'X-API-Key: ***'),
]


def configure_logging(
    log_level: Optional[str] = None,
    service_name: str = "api-gateway",
    environment: Optional[str] = None,
) -> None:
    """Configure structured logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        service_name: Service name for logs
        environment: Environment name
    """
    level = log_level or settings.log_level
    env = environment or settings.environment
    
    # Configure basic logging
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    
    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


class Logger:
    """Simple logger wrapper with context."""
    
    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)
    
    def _redact_sensitive(self, message: str) -> str:
        """Redact sensitive data from message."""
        import re
        for pattern, replacement in SENSITIVE_PATTERNS:
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
        return message
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._logger.debug(self._format_message(message, kwargs))
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._logger.info(self._format_message(message, kwargs))
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._logger.warning(self._format_message(message, kwargs))
    
    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self._logger.error(self._format_message(message, kwargs))
    
    def _format_message(self, message: str, context: dict[str, Any]) -> str:
        """Format message with context."""
        if context:
            context_str = " ".join(f"{k}={v}" for k, v in context.items())
            full_message = f"{message} | {context_str}"
        else:
            full_message = message
        return self._redact_sensitive(full_message)


def get_logger(name: str) -> Logger:
    """Get logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return Logger(name)

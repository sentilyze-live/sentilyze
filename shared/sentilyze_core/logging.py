"""Structured JSON logging configuration."""

import logging
import sys
from typing import Any

import structlog
from pythonjsonlogger import jsonlogger


def _gcp_severity_and_message(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Ensure GCP Logging friendly fields in structured JSON logs.

    - Adds `severity` (uppercase) derived from structlog `level`
    - Adds `message` derived from structlog `event`
    """
    level = event_dict.get("level")
    if level and "severity" not in event_dict:
        event_dict["severity"] = str(level).upper()
    if "message" not in event_dict and "event" in event_dict:
        event_dict["message"] = event_dict["event"]
    return event_dict


def configure_logging(
    log_level: str = "INFO",
    service_name: str = "sentilyze",
    environment: str = "development",
) -> None:
    """Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        service_name: Name of the service
        environment: Deployment environment
    """
    # Configure standard library logging
    log_format = "%(asctime)s %(levelname)s %(name)s %(message)s"

    if environment == "production":
        # JSON formatter for production
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "severity"},
        )
    else:
        # Human-readable formatter for development
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers = []

    # Add stream handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Configure structlog
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.stdlib.add_logger_name,
        _gcp_severity_and_message,
    ]

    if environment == "production":
        # Additional processors for production
        structlog_processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Pretty printing for development
        try:
            import colorama  # noqa: F401
            use_colors = True
        except Exception:
            use_colors = False
        structlog_processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=use_colors),
        ]

    structlog.configure(
        processors=structlog_processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Add service context
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        service=service_name,
        environment=environment,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)

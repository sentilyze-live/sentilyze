"""Alert Service configuration.

This module re-exports settings from sentilyze_core for backward compatibility.
All configuration is now centralized in sentilyze_core.Settings.
"""

from enum import Enum

from sentilyze_core import Settings, get_settings


class AlertChannel(Enum):
    """Alert notification channels."""

    TELEGRAM = "telegram"
    WEBHOOK = "webhook"
    EMAIL = "email"
    SLACK = "slack"


class AlertSeverity(Enum):
    """Alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Re-export settings for backward compatibility
AlertSettings = Settings
get_alert_settings = get_settings


__all__ = [
    "AlertChannel",
    "AlertSeverity",
    "AlertSettings",
    "get_alert_settings",
]

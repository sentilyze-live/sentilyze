"""API Gateway configuration.

This module re-exports settings from sentilyze_core for backward compatibility.
All configuration is now centralized in sentilyze_core.Settings.
"""

from sentilyze_core import Settings, get_settings


# Re-export settings for backward compatibility - API Gateway already uses get_settings
__all__ = [
    "Settings",
    "get_settings",
]

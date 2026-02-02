"""Tracker Service configuration.

This module re-exports settings from sentilyze_core for backward compatibility.
All configuration is now centralized in sentilyze_core.Settings.
"""

from enum import Enum

from sentilyze_core import Settings, get_settings


class SuccessLevel(Enum):
    """Prediction success levels."""

    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    FAILED = "failed"


# Re-export settings for backward compatibility
TrackerSettings = Settings
get_tracker_settings = get_settings


__all__ = [
    "SuccessLevel",
    "TrackerSettings",
    "get_tracker_settings",
]

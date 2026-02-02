"""Prediction Engine configuration.

This module re-exports settings from sentilyze_core for backward compatibility.
All configuration is now centralized in sentilyze_core.Settings.
"""

from enum import Enum

from sentilyze_core import Settings, get_settings


class PredictionType(Enum):
    """Prediction timeframes."""

    THIRTY_MINUTE = "30m"
    ONE_HOUR = "1h"
    THREE_HOUR = "3h"
    SIX_HOUR = "6h"
    ONE_DAY = "1d"


class PredictionDirection(Enum):
    """Predicted price direction."""

    UP = "UP"
    DOWN = "DOWN"
    FLAT = "FLAT"


class ConfidenceLevel(Enum):
    """Confidence level classifications."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# Re-export settings for backward compatibility
PredictionSettings = Settings
get_prediction_settings = get_settings


__all__ = [
    "PredictionType",
    "PredictionDirection",
    "ConfidenceLevel",
    "PredictionSettings",
    "get_prediction_settings",
]

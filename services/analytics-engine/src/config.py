"""Analytics Engine configuration.

This module re-exports settings from sentilyze_core for backward compatibility.
All configuration is now centralized in sentilyze_core.Settings.
"""

from enum import Enum

from sentilyze_core import Settings, get_settings


class AnalysisType(Enum):
    """Types of analytics analysis."""

    CORRELATION = "correlation"
    GRANGER = "granger"
    BACKTEST = "backtest"
    SENTIMENT_TREND = "sentiment_trend"
    PRICE_TREND = "price_trend"


# Re-export settings for backward compatibility
AnalyticsSettings = Settings
get_analytics_settings = get_settings


__all__ = [
    "AnalysisType",
    "AnalyticsSettings",
    "get_analytics_settings",
]

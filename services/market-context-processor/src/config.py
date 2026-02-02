"""Market Context Processor configuration.

This module re-exports settings from sentilyze_core for backward compatibility.
All configuration is now centralized in sentilyze_core.Settings.
"""

from enum import Enum

from sentilyze_core import Settings, get_settings


class MarketRegime(Enum):
    """Market regime classification."""

    BULL = "bull"
    BEAR = "bear"
    NEUTRAL = "neutral"
    VOLATILE = "volatile"


class TrendDirection(Enum):
    """Trend direction classification."""

    UP = "up"
    DOWN = "down"
    SIDEWAYS = "sideways"


class VolatilityRegime(Enum):
    """Volatility classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class CorrelationStrength(Enum):
    """Interpretation of correlation strength."""

    VERY_STRONG_NEGATIVE = "very_strong_negative"
    STRONG_NEGATIVE = "strong_negative"
    MODERATE_NEGATIVE = "moderate_negative"
    WEAK = "weak"
    MODERATE_POSITIVE = "moderate_positive"
    STRONG_POSITIVE = "strong_positive"
    VERY_STRONG_POSITIVE = "very_strong_positive"


class AnomalyType(Enum):
    """Types of market anomalies."""

    PRICE_SENTIMENT_DIVERGENCE = "price_sentiment_divergence"
    SUDDEN_PRICE_MOVE = "sudden_price_move"
    VOLUME_SPIKE = "volume_spike"
    VOLATILITY_SPIKE = "volatility_spike"
    SUPPORT_BREAK = "support_break"
    RESISTANCE_BREAK = "resistance_break"
    FLASH_CRASH = "flash_crash"
    FLASH_PUMP = "flash_pump"


class AnomalySeverity(Enum):
    """Severity levels for anomalies."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Re-export settings for backward compatibility
MarketContextSettings = Settings
get_market_context_settings = get_settings


__all__ = [
    "MarketRegime",
    "TrendDirection",
    "VolatilityRegime",
    "CorrelationStrength",
    "AnomalyType",
    "AnomalySeverity",
    "MarketContextSettings",
    "get_market_context_settings",
]

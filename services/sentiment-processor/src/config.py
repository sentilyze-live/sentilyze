"""Configuration and enums for the unified sentiment processor.

This module provides service-specific enums and re-exports from sentilyze_core.
"""

from enum import Enum
from typing import Literal

from sentilyze_core import MarketType, SentimentLabel, MacroIndicatorType


class AnalysisMode(Enum):
    """Analysis mode for sentiment processing."""

    LITE = "lite"
    DEEP = "deep"
    AUTO = "auto"


class CotPositionType(Enum):
    """COT (Commitment of Traders) position types."""

    PRODUCER = "producer"
    SWAP_DEALER = "swap_dealer"
    MONEY_MANAGER = "money_manager"
    OTHER_REPORTABLE = "other_reportable"
    NON_REPORTABLE = "non_reportable"


class PriceImplication(Enum):
    """Price implications for sentiment analysis."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class TimeHorizon(Enum):
    """Time horizons for sentiment predictions."""

    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"


# Feature flag helpers
def is_market_enabled(
    market_type: MarketType, crypto_enabled: bool = True, gold_enabled: bool = True
) -> bool:
    """Check if a market type is enabled based on feature flags."""
    if market_type == MarketType.CRYPTO:
        return crypto_enabled
    elif market_type == MarketType.GOLD:
        return gold_enabled
    # For any other markets, don't block by default.
    return True


def get_default_market_type() -> MarketType:
    """Get the default market type for analysis."""
    # sentilyze_core.MarketType does not have a GENERIC value; default to CRYPTO.
    return MarketType.CRYPTO


__all__ = [
    # Re-exported from sentilyze_core
    "MarketType",
    "SentimentLabel",
    "MacroIndicatorType",
    # Service-specific enums
    "AnalysisMode",
    "CotPositionType",
    "PriceImplication",
    "TimeHorizon",
    # Helper functions
    "is_market_enabled",
    "get_default_market_type",
]

"""Sentilyze Core - Unified shared library for Sentilyze v4 microservices.

This library provides common functionality for both crypto and gold market sentiment analysis.
"""

__version__ = "4.0.0"

from .config import Settings, get_settings
from .logging import get_logger, configure_logging
from .pubsub import PubSubClient, PubSubMessage
from .bigquery import BigQueryClient
from .cache import CacheClient
from .firestore_cache import FirestoreCacheClient, get_cache_client
from .models import (
    BaseModel,
    SentimentResult,
    RawEvent,
    ProcessedEvent,
    AlertEvent,
    AnalyticsMetric,
    DataSource,
    SentimentLabel,
    # Asset types
    CryptoAssetType,
    GoldAssetType,
    MetalAssetType,
    # Market context
    CryptoMarketContext,
    GoldMarketContext,
    MetalMarketContext,
    # Analysis models
    SentimentAnalysis,
    CryptoSentimentAnalysis,
    GoldSentimentAnalysis,
    MetalSentimentAnalysis,
    # Enums
    MarketType,
    MacroIndicatorType,
    CryptoIndicatorType,
)
from .exceptions import (
    SentilyzeError,
    ConfigurationError,
    PubSubError,
    BigQueryError,
    CacheError,
    ValidationError,
)
from .circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerOpen,
    goldapi_circuit,
    finnhub_circuit,
    alphavantage_circuit,
    cryptoapi_circuit,
)
from .metrics import (
    initialize_metrics,
    track_request,
    track_collection,
    track_sentiment_analysis,
)

__all__ = [
    # Version
    "__version__",
    # Config
    "Settings",
    "get_settings",
    # Logging
    "get_logger",
    "configure_logging",
    # Pub/Sub
    "PubSubClient",
    "PubSubMessage",
    # Clients
    "BigQueryClient",
    "CacheClient",
    "FirestoreCacheClient",
    "get_cache_client",
    # Base Models
    "BaseModel",
    "SentimentResult",
    "RawEvent",
    "ProcessedEvent",
    "AlertEvent",
    "AnalyticsMetric",
    "DataSource",
    "SentimentLabel",
    # Market Types
    "MarketType",
    "CryptoAssetType",
    "GoldAssetType",
    "MetalAssetType",
    # Market Context
    "CryptoMarketContext",
    "GoldMarketContext",
    "MetalMarketContext",
    # Analysis Models
    "SentimentAnalysis",
    "CryptoSentimentAnalysis",
    "GoldSentimentAnalysis",
    "MetalSentimentAnalysis",
    # Indicators
    "MacroIndicatorType",
    "CryptoIndicatorType",
    # Exceptions
    "SentilyzeError",
    "ConfigurationError",
    "PubSubError",
    "BigQueryError",
    "CacheError",
    "ValidationError",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitState",
    "CircuitBreakerOpen",
    "goldapi_circuit",
    "finnhub_circuit",
    "alphavantage_circuit",
    "cryptoapi_circuit",
    # Metrics
    "initialize_metrics",
    "track_request",
    "track_collection",
    "track_sentiment_analysis",
]

"""Common Pydantic models for data validation.

Unified models supporting both crypto and gold/precious metals markets.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field


class BaseModel(PydanticBaseModel):
    """Base model with common configuration."""

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class MarketType(str, Enum):
    """Market types supported by Sentilyze."""
    
    CRYPTO = "crypto"
    GOLD = "gold"
    METALS = "metals"
    FOREX = "forex"
    STOCKS = "stocks"


class DataSource(str, Enum):
    """Data source types for all markets."""

    # Social/Media
    REDDIT = "reddit"
    TWITTER = "twitter"
    RSS = "rss"
    CRYPTOPANIC = "cryptopanic"
    CUSTOM = "custom"
    
    # Crypto-specific
    BINANCE = "binance"
    COINGECKO = "coingecko"
    COINMARKETCAP = "coinmarketcap"
    CRYPTOCOMPARE = "cryptocompare"
    
    # Financial/Traditional
    ALPHA_VANTAGE = "alpha_vantage"
    FINNHUB = "finnhub"
    FRED = "fred"
    EODHD = "eodhd"
    COMMON_CRAWL = "common_crawl"
    SANTIMENT = "santiment"
    LUNARCRUSH = "lunarcrush"
    
    # Gold/Metals-specific
    GOLDAPI = "goldapi"
    METALS_API = "metals_api"
    TWELVE_DATA = "twelve_data"
    WORLD_GOLD_COUNCIL = "world_gold_council"
    LONDON_BULLION = "london_bullion"


class SentimentLabel(str, Enum):
    """Sentiment classification labels."""

    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class SentimentResult(BaseModel):
    """Sentiment analysis result."""

    score: float = Field(..., ge=-1.0, le=1.0, description="Sentiment score from -1 to 1")
    label: SentimentLabel = Field(..., description="Sentiment classification")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    explanation: Optional[str] = Field(default=None, description="Explanation of the sentiment")
    model_used: str = Field(default="gemini-1.5-flash", description="Model used for analysis")
    processed_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Crypto Asset Types
# =============================================================================


class CryptoAssetType(str, Enum):
    """Cryptocurrency asset types."""
    
    BTC = "btc"
    ETH = "eth"
    BNB = "bnb"
    XRP = "xrp"
    ADA = "ada"
    SOL = "sol"
    DOT = "dot"
    AVAX = "avax"
    MATIC = "matic"
    LINK = "link"
    UNI = "uni"
    AAVE = "aave"
    SUSHI = "sushi"
    COMP = "comp"
    MKR = "mkr"
    YFI = "yfi"
    SNX = "snx"
    CRV = "crv"
    # Stablecoins
    USDT = "usdt"
    USDC = "usdc"
    DAI = "dai"
    BUSD = "busd"
    # DeFi tokens
    LDO = "ldo"
    LUNC = "lunc"
    SHIB = "shib"
    DOGE = "doge"


# =============================================================================
# Gold/Metals Asset Types
# =============================================================================


class GoldAssetType(str, Enum):
    """Gold and precious metals asset types."""

    XAUUSD = "xauusd"  # Gold / US Dollar
    XAUEUR = "xaueur"  # Gold / Euro
    XAUGBP = "xaugbp"  # Gold / British Pound
    XAUTRY = "xautry"  # Gold / Turkish Lira
    XAGUSD = "xagusd"  # Silver / US Dollar
    XPTUSD = "xptusd"  # Platinum / US Dollar
    XPDUSD = "xpdusd"  # Palladium / US Dollar
    GLD = "gld"  # SPDR Gold Shares ETF
    IAU = "iau"  # iShares Gold Trust ETF


class MetalAssetType(str, Enum):
    """Extended precious metals asset types."""
    
    XAU = "xau"  # Gold
    XAG = "xag"  # Silver
    XPT = "xpt"  # Platinum
    XPD = "xpd"  # Palladium
    XRH = "xrh"  # Rhodium
    XRU = "xru"  # Ruthenium
    XIR = "xir"  # Iridium
    XOS = "xos"  # Osmium


# Union type for any asset
AnyAssetType = Union[CryptoAssetType, GoldAssetType, MetalAssetType, str]


# =============================================================================
# Event Models
# =============================================================================


class RawEvent(BaseModel):
    """Raw data event from ingestion (Bronze layer)."""

    event_id: UUID = Field(default_factory=uuid4)
    source: DataSource = Field(..., description="Data source")
    source_id: str = Field(..., description="Unique identifier from source")
    market_type: MarketType = Field(default=MarketType.CRYPTO, description="Market type")
    # Text content for NLP. Some sources are structured (market data); for those,
    # content may be empty and `payload` will contain the structured raw data.
    content: str = Field(default="", description="Raw content (text)")
    data_type: Optional[str] = Field(
        default=None,
        description="Optional data type hint (news, market_data, ohlcv, etc.)",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw structured payload (when applicable)",
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Source-specific metadata")
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: Optional[str] = Field(default=None, description="Multi-tenancy support")

    # Source-specific fields
    author: Optional[str] = Field(default=None)
    url: Optional[str] = Field(default=None)
    title: Optional[str] = Field(default=None)
    published_at: Optional[datetime] = Field(default=None)
    symbols: list[str] = Field(default_factory=list, description="Assets mentioned")
    
    # Market-specific context
    asset_type: Optional[str] = Field(default=None, description="Asset type classification")


class ProcessedEvent(BaseModel):
    """Processed event with sentiment (Silver layer)."""

    event_id: UUID = Field(..., description="Reference to raw event")
    source: DataSource = Field(...)
    market_type: MarketType = Field(default=MarketType.CRYPTO)
    content: str = Field(..., description="Processed/cleaned content")
    sentiment: SentimentResult = Field(...)
    entities: list[str] = Field(default_factory=list, description="Named entities")
    symbols: list[str] = Field(default_factory=list, description="Detected asset symbols")
    keywords: list[str] = Field(default_factory=list)
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: Optional[str] = Field(default=None)

    # Analytics fields
    engagement_score: Optional[float] = Field(default=None)
    reach_estimate: Optional[int] = Field(default=None)
    
    # Market-specific analysis results
    market_context: Optional[dict[str, Any]] = Field(
        default=None,
        description="Market-specific context (crypto or gold)",
    )


class AlertEvent(BaseModel):
    """Alert event for notifications."""

    alert_id: UUID = Field(default_factory=uuid4)
    alert_type: str = Field(..., description="Type of alert")
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    title: str = Field(...)
    message: str = Field(...)
    market_type: MarketType = Field(default=MarketType.CRYPTO)
    data: dict[str, Any] = Field(default_factory=dict)
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: Optional[str] = Field(default=None)

    # Alert routing
    channels: list[str] = Field(default_factory=list, description="Notification channels")
    recipients: list[str] = Field(default_factory=list)
    
    # Market-specific data
    affected_assets: list[str] = Field(default_factory=list, description="Assets affected by alert")
    sentiment_snapshot: Optional[SentimentResult] = Field(default=None)


class TimeRange(BaseModel):
    """Time range for queries."""

    start: datetime = Field(...)
    end: datetime = Field(...)

    @property
    def duration_seconds(self) -> float:
        """Calculate duration in seconds."""
        return (self.end - self.start).total_seconds()


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        """Calculate offset for SQL queries."""
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""

    items: list[Any] = Field(default_factory=list)
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)
    total_pages: int = Field(..., ge=0)

    @classmethod
    def create(
        cls,
        items: list[Any],
        total: int,
        pagination: PaginationParams,
    ) -> "PaginatedResponse":
        """Create paginated response."""
        total_pages = (total + pagination.page_size - 1) // pagination.page_size
        return cls(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
        )


class AnalyticsMetric(BaseModel):
    """Analytics metric row (matches BigQuery `analytics` table schema)."""

    metric: str = Field(..., description="Metric name (e.g., avg_sentiment)")
    value: Optional[float] = Field(default=None, description="Metric value")
    window_start: Optional[datetime] = Field(default=None)
    window_end: Optional[datetime] = Field(default=None)
    market_type: MarketType = Field(default=MarketType.CRYPTO)
    symbol: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Market Indicators
# =============================================================================


class MacroIndicatorType(str, Enum):
    """Macroeconomic indicators affecting asset prices."""

    FED_RATE = "fed_rate"  # Federal Reserve interest rate
    CPI = "cpi"  # Consumer Price Index (inflation)
    PPI = "ppi"  # Producer Price Index
    NFP = "nfp"  # Non-Farm Payrolls
    GDP = "gdp"  # Gross Domestic Product
    DXY = "dxy"  # US Dollar Index
    US10Y = "us10y"  # US 10-Year Treasury Yield
    US30Y = "us30y"  # US 30-Year Treasury Yield
    VIX = "vix"  # Volatility Index
    GEOPOLITICAL = "geopolitical"  # Geopolitical events
    INFLATION_EXPECTATIONS = "inflation_expectations"


class CryptoIndicatorType(str, Enum):
    """Crypto-specific market indicators."""

    DOMINANCE = "dominance"  # Market dominance
    NETWORK_ACTIVITY = "network_activity"
    TRANSACTION_VOLUME = "transaction_volume"
    MINING_DIFFICULTY = "mining_difficulty"
    HASH_RATE = "hash_rate"
    ACTIVE_ADDRESSES = "active_addresses"
    EXCHANGE_INFLOW = "exchange_inflow"
    EXCHANGE_OUTFLOW = "exchange_outflow"
    FUNDING_RATE = "funding_rate"
    OPEN_INTEREST = "open_interest"
    LIQUIDATIONS = "liquidations"


# =============================================================================
# Market Context Models
# =============================================================================


class PriceData(BaseModel):
    """Generic price data structure for any asset."""

    symbol: str = Field(..., description="Asset symbol")
    currency: str = Field(..., description="Quote currency (USD, EUR, etc.)")
    pair: str = Field(..., description="Trading pair (e.g., BTCUSD)")
    price: float = Field(..., description="Current spot price")
    open_price: Optional[float] = Field(default=None, description="Opening price")
    high_price: Optional[float] = Field(default=None, description="Daily high")
    low_price: Optional[float] = Field(default=None, description="Daily low")
    change: float = Field(default=0.0, description="Price change")
    change_percent: float = Field(default=0.0, description="Price change percentage")
    volume_24h: Optional[float] = Field(default=None, description="24h trading volume")
    timestamp: datetime = Field(..., description="Price timestamp")


class CryptoMarketContext(BaseModel):
    """Market context for crypto analysis."""
    
    regime: str = Field(..., description="Market regime (bull, bear, neutral, crab)")
    trend_direction: str = Field(..., description="Trend direction (up, down, sideways)")
    volatility_regime: str = Field(..., description="Volatility level (low, medium, high)")
    support_level: Optional[float] = Field(default=None)
    resistance_level: Optional[float] = Field(default=None)
    rsi_14d: Optional[float] = Field(default=None, description="14-day RSI")
    sma_50: Optional[float] = Field(default=None, description="50-day SMA")
    sma_200: Optional[float] = Field(default=None, description="200-day SMA")
    dominance: Optional[float] = Field(default=None, description="Market dominance %")
    funding_rate: Optional[float] = Field(default=None)
    open_interest: Optional[float] = Field(default=None)
    exchange_inflow: Optional[float] = Field(default=None)
    network_activity: Optional[float] = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GoldMarketContext(BaseModel):
    """Market context for gold/precious metals analysis."""

    regime: str = Field(..., description="Market regime (bull, bear, neutral)")
    trend_direction: str = Field(..., description="Trend direction (up, down, sideways)")
    volatility_regime: str = Field(..., description="Volatility level (low, medium, high)")
    support_level: Optional[float] = Field(default=None, description="Key support level")
    resistance_level: Optional[float] = Field(default=None, description="Key resistance level")
    rsi_14d: Optional[float] = Field(default=None, description="14-day RSI")
    sma_50: Optional[float] = Field(default=None, description="50-day SMA")
    sma_200: Optional[float] = Field(default=None, description="200-day SMA")
    correlation_dxy: Optional[float] = Field(default=None, description="Correlation with DXY")
    safe_haven_flow: Optional[float] = Field(default=None, description="Safe haven demand indicator")
    central_bank_demand: Optional[float] = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MetalMarketContext(BaseModel):
    """Market context for metals analysis (gold + other metals)."""

    metal_type: Optional[MetalAssetType] = Field(
        default=None,
        description="Metal type (XAU, XAG, XPT, etc.)",
    )
    regime: str = Field(..., description="Market regime (bull, bear, neutral)")
    trend_direction: str = Field(..., description="Trend direction (up, down, sideways)")
    volatility_regime: str = Field(..., description="Volatility level (low, medium, high)")
    support_level: Optional[float] = Field(default=None, description="Key support level")
    resistance_level: Optional[float] = Field(default=None, description="Key resistance level")
    rsi_14d: Optional[float] = Field(default=None, description="14-day RSI")
    sma_50: Optional[float] = Field(default=None, description="50-day SMA")
    sma_200: Optional[float] = Field(default=None, description="200-day SMA")
    correlation_dxy: Optional[float] = Field(default=None, description="Correlation with DXY")
    safe_haven_flow: Optional[float] = Field(default=None, description="Safe haven demand indicator")
    central_bank_demand: Optional[float] = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Unified market context type
MarketContext = Union[CryptoMarketContext, GoldMarketContext, MetalMarketContext]


class MacroForce(BaseModel):
    """Macroeconomic force affecting assets."""

    indicator: MacroIndicatorType = Field(..., description="Indicator type")
    value: float = Field(..., description="Current value")
    previous_value: Optional[float] = Field(default=None, description="Previous value")
    impact: str = Field(..., description="Impact level (high, medium, low)")
    direction: str = Field(..., description="Direction (positive, negative, neutral)")
    description: Optional[str] = Field(default=None, description="Description of the force")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CryptoForce(BaseModel):
    """Crypto-specific market force."""
    
    indicator: CryptoIndicatorType = Field(..., description="Indicator type")
    value: float = Field(..., description="Current value")
    previous_value: Optional[float] = Field(default=None)
    impact: str = Field(..., description="Impact level (high, medium, low)")
    direction: str = Field(..., description="Direction (positive, negative, neutral)")
    description: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Sentiment Analysis Models
# =============================================================================


class SentimentAnalysis(BaseModel):
    """Generic sentiment analysis result."""
    
    sentiment: SentimentResult = Field(..., description="Base sentiment result")
    entities: list[str] = Field(default_factory=list, description="Named entities")
    key_drivers: list[str] = Field(default_factory=list, description="Key drivers identified")
    price_implication: Optional[str] = Field(
        default=None,
        description="Price implication (bullish, bearish, neutral)",
    )
    confidence_factors: list[str] = Field(
        default_factory=list,
        description="Factors affecting confidence",
    )
    market_type: MarketType = Field(default=MarketType.CRYPTO)


class CryptoSentimentAnalysis(SentimentAnalysis):
    """Crypto-specific sentiment analysis result."""
    
    market_type: MarketType = Field(default=MarketType.CRYPTO)
    crypto_forces: list[CryptoForce] = Field(
        default_factory=list,
        description="Identified crypto-specific forces",
    )
    market_context: Optional[CryptoMarketContext] = Field(
        default=None,
        description="Current crypto market context",
    )
    on_chain_signals: list[str] = Field(default_factory=list, description="On-chain indicators")
    exchange_signals: list[str] = Field(default_factory=list, description="Exchange flow signals")
    social_metrics: Optional[dict[str, float]] = Field(
        default=None,
        description="Social media metrics",
    )


class GoldSentimentAnalysis(SentimentAnalysis):
    """Gold-specific sentiment analysis result."""

    market_type: MarketType = Field(default=MarketType.GOLD)
    macro_forces: list[MacroForce] = Field(
        default_factory=list,
        description="Identified macro forces",
    )
    market_context: Optional[GoldMarketContext] = Field(
        default=None,
        description="Current gold market context",
    )


class MetalSentimentAnalysis(GoldSentimentAnalysis):
    """Precious metals sentiment analysis (extends gold)."""
    
    market_type: MarketType = Field(default=MarketType.METALS)
    market_context: Optional[MetalMarketContext] = Field(
        default=None,
        description="Current metals market context",
    )
    metal_type: MetalAssetType = Field(default=MetalAssetType.XAU)
    industrial_demand: Optional[float] = Field(default=None)
    jewelry_demand: Optional[float] = Field(default=None)
    investment_demand: Optional[float] = Field(default=None)


# =============================================================================
# Alert Models
# =============================================================================


class CryptoAlert(BaseModel):
    """Crypto-specific alert event."""

    alert_id: UUID = Field(default_factory=uuid4)
    alert_type: str = Field(..., description="Alert type")
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    title: str = Field(...)
    message: str = Field(...)
    assets: list[CryptoAssetType] = Field(default_factory=list)
    trigger_price: Optional[float] = Field(default=None)
    sentiment_score: Optional[float] = Field(default=None)
    volume_spike: Optional[float] = Field(default=None)
    social_mentions_spike: Optional[float] = Field(default=None)
    data: dict[str, Any] = Field(default_factory=dict)
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    channels: list[str] = Field(default_factory=list)
    recipients: list[str] = Field(default_factory=list)


class GoldAlert(BaseModel):
    """Gold/metals-specific alert event."""

    alert_id: UUID = Field(default_factory=uuid4)
    alert_type: str = Field(..., description="Alert type")
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    title: str = Field(...)
    message: str = Field(...)
    assets: list[GoldAssetType] = Field(default_factory=list)
    trigger_price: Optional[float] = Field(default=None)
    sentiment_score: Optional[float] = Field(default=None)
    macro_context: Optional[dict[str, Any]] = Field(default=None)
    data: dict[str, Any] = Field(default_factory=dict)
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    channels: list[str] = Field(default_factory=list)
    recipients: list[str] = Field(default_factory=list)

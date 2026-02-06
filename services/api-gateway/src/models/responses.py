"""Pydantic response models for standardized API responses.

All models use snake_case field names (Python convention).
The transformation middleware will convert to camelCase for frontend.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Optional


# ============================================================================
# Price Response Models
# ============================================================================

class PriceData(BaseModel):
    """Gold price data response model."""
    symbol: str
    price: float
    timestamp: datetime
    change: float = 0.0
    change_percent: float = 0.0
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    volume: Optional[float] = None
    currency: str = "USD"
    data_source: str = "goldapi"

    class Config:
        populate_by_name = True


# ============================================================================
# Sentiment Response Models
# ============================================================================

class SentimentAggregate(BaseModel):
    """Aggregated sentiment metrics."""
    score: float
    confidence: float
    sentiment_count: int
    label: str  # positive, negative, neutral


class SentimentData(BaseModel):
    """Sentiment analysis response model."""
    symbol: str
    aggregate: SentimentAggregate
    sources: Dict[str, float]  # source_name: avg_score
    period: Dict[str, str]  # start, end
    timestamp: datetime
    data_source: str = "bigquery"


# ============================================================================
# Prediction Response Models
# ============================================================================

class PredictionItem(BaseModel):
    """Single timeframe prediction."""
    timeframe: str  # 1h, 2h, 3h, 24h, 7d
    predicted_price: float
    change_percent: float
    confidence: float  # 0-1
    direction: str  # up, down
    models_used: int


class PredictionsData(BaseModel):
    """Gold price predictions response model."""
    symbol: str
    current_price: float
    predictions: List[PredictionItem]
    prediction_method: str = "ensemble"
    sentiment_score: Optional[float] = None
    sentiment_source: Optional[str] = None
    sentiment_count: Optional[int] = None
    price_source: str = "goldapi"
    generated_at: datetime
    disclaimer: str = "Predictions are for informational purposes only and not investment advice."


# ============================================================================
# Market Context Response Models
# ============================================================================

class MarketContextData(BaseModel):
    """Market context analysis response model."""
    symbol: str
    trend_direction: str  # up, down, sideways
    trend_strength: float  # 0-1
    volatility_regime: str  # low, normal, high
    volatility_value: float  # 0-1
    technical_levels: Dict[str, List[float]]  # support, resistance
    factors: Dict[str, float]  # usd_strength, interest_rates, geopolitical_risk
    timestamp: datetime
    data_source: str = "bigquery"


# ============================================================================
# Technical Indicators Response Models
# ============================================================================

class RSIData(BaseModel):
    """RSI indicator data."""
    value: float
    condition: str  # oversold, neutral, overbought


class MACDData(BaseModel):
    """MACD indicator data."""
    value: float
    signal: float
    momentum: str  # positive, negative
    histogram: float


class BollingerBandsData(BaseModel):
    """Bollinger Bands data."""
    upper: float
    middle: float
    lower: float
    width: float


class SMAData(BaseModel):
    """Simple Moving Averages."""
    sma_20: float = Field(alias="20")
    sma_50: float = Field(alias="50")
    sma_200: float = Field(alias="200")

    class Config:
        populate_by_name = True


class TechnicalIndicatorsData(BaseModel):
    """Technical indicators response model."""
    symbol: str
    current_price: float
    rsi: RSIData
    macd: MACDData
    bollinger: BollingerBandsData
    sma: Dict[str, float]  # "20", "50", "200"
    data_points: int
    data_source: str
    generated_at: datetime


# ============================================================================
# News Response Models
# ============================================================================

class NewsArticle(BaseModel):
    """Single news article."""
    id: str
    title: str
    source: str
    url: str
    timestamp: datetime
    sentiment: Optional[float] = None


class NewsPagination(BaseModel):
    """Pagination metadata."""
    page: int
    limit: int
    total: int
    has_more: bool


class NewsResponse(BaseModel):
    """News articles response model."""
    articles: List[NewsArticle]
    pagination: NewsPagination
    data_source: str = "bigquery"


# ============================================================================
# Scenarios Response Models
# ============================================================================

class ModelWeight(BaseModel):
    """Model weight in scenario."""
    name: str  # LSTM, XGBoost, ARIMA, Random Forest
    weight: float  # 0-1
    prediction: float


class ScenarioModel(BaseModel):
    """Single scenario model."""
    timeframe: str
    price: float
    change_percent: float
    confidence_score: float
    direction: str  # up, down
    models: List[ModelWeight]
    num_models_used: int
    sentiment_score: Optional[float] = None
    sentiment_source: Optional[str] = None


class ScenariosData(BaseModel):
    """Scenarios response model."""
    symbol: str
    ensemble_prediction: float
    ensemble_confidence: float
    scenarios: Dict[str, List[ScenarioModel]]  # "1h", "2h", "3h"
    timestamp: datetime


# ============================================================================
# Daily Report Response Models
# ============================================================================

class ModelPerformance(BaseModel):
    """Model performance metrics."""
    model_name: str
    accuracy: float  # 0-1
    predictions_count: int


class DailyReportData(BaseModel):
    """Daily prediction report response model."""
    date: str  # YYYY-MM-DD
    overall_accuracy: float
    total_predictions: int
    correct_predictions: int
    models: List[ModelPerformance]
    period_days: int = 7


# ============================================================================
# Correlation Response Models
# ============================================================================

class CorrelationDetail(BaseModel):
    """Correlation analysis detail."""
    correlation: float  # -1 to 1
    strength: str  # strong, moderate, weak
    direction: str  # positive, negative
    interpretation: str


class CorrelationData(BaseModel):
    """Correlation response model."""
    symbol: str
    comparisons: Dict[str, CorrelationDetail]  # asset_symbol: detail
    period: Dict[str, str]  # start, end
    timestamp: datetime

"""Data models for the Prediction Engine."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .config import ConfidenceLevel, PredictionDirection, PredictionType


@dataclass
class TechnicalIndicators:
    """Technical indicator results."""
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    ema_short: Optional[float] = None
    ema_medium: Optional[float] = None
    ema_long: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            "rsi": self.rsi,
            "macd": self.macd,
            "macd_signal": self.macd_signal,
            "macd_histogram": self.macd_histogram,
            "bb_upper": self.bb_upper,
            "bb_middle": self.bb_middle,
            "bb_lower": self.bb_lower,
            "ema_short": self.ema_short,
            "ema_medium": self.ema_medium,
            "ema_long": self.ema_long,
        }


@dataclass
class PredictionResult:
    """Prediction result."""
    prediction_id: str
    prediction_type: str
    market_type: str
    symbol: str
    current_price: float
    predicted_price: float
    predicted_direction: PredictionDirection
    confidence_score: int
    confidence_level: ConfidenceLevel
    technical_indicators: TechnicalIndicators
    sentiment_score: float
    reasoning: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    status: str = "pending"  # pending, completed, expired
    
    def to_dict(self) -> dict:
        return {
            "prediction_id": self.prediction_id,
            "prediction_type": self.prediction_type,
            "market_type": self.market_type,
            "symbol": self.symbol,
            "current_price": self.current_price,
            "predicted_price": self.predicted_price,
            "predicted_direction": self.predicted_direction.value,
            "confidence_score": self.confidence_score,
            "confidence_level": self.confidence_level.value,
            "technical_indicators": self.technical_indicators.to_dict(),
            "sentiment_score": self.sentiment_score,
            "reasoning": self.reasoning,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status,
        }


@dataclass
class PredictionOutcome:
    """Prediction outcome after expiration."""
    prediction_id: str
    actual_price: float
    actual_direction: PredictionDirection
    price_diff: float
    percent_diff: float
    direction_correct: bool
    success_level: str  # EXCELLENT, GOOD, ACCEPTABLE, FAILED
    ai_analysis: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "prediction_id": self.prediction_id,
            "actual_price": self.actual_price,
            "actual_direction": self.actual_direction.value,
            "price_diff": self.price_diff,
            "percent_diff": self.percent_diff,
            "direction_correct": self.direction_correct,
            "success_level": self.success_level,
            "ai_analysis": self.ai_analysis,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ModelMetrics:
    """ML model performance metrics."""
    total_predictions: int = 0
    correct_directions: int = 0
    accuracy: float = 0.0
    avg_price_error: float = 0.0
    last_trained: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "total_predictions": self.total_predictions,
            "correct_directions": self.correct_directions,
            "accuracy": self.accuracy,
            "avg_price_error": self.avg_price_error,
            "last_trained": self.last_trained.isoformat() if self.last_trained else None,
        }

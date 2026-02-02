"""Data models for the Tracker Service."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class PredictionRecord:
    """Record of a prediction."""
    prediction_id: str
    user_id: str
    symbol: str
    market_type: str
    prediction_type: str  # 30m, 1h, 3h, 6h
    current_price: float
    predicted_price: float
    predicted_direction: str  # UP, DOWN, FLAT
    confidence_score: int
    confidence_level: str  # LOW, MEDIUM, HIGH
    technical_signals: dict
    sentiment_score: float
    reasoning: str
    status: str = "pending"  # pending, completed, expired
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


@dataclass
class PredictionOutcome:
    """Outcome of a prediction."""
    outcome_id: str
    prediction_id: str
    actual_price: float
    actual_direction: str  # UP, DOWN, FLAT
    price_diff: float
    percent_diff: float
    direction_correct: bool
    success_level: str  # EXCELLENT, GOOD, ACCEPTABLE, FAILED
    ai_analysis: Optional[str] = None
    ai_analysis_generated: bool = False
    learning_insights: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AccuracyStats:
    """Accuracy statistics for predictions."""
    total_predictions: int = 0
    correct_directions: int = 0
    accuracy_percentage: float = 0.0
    avg_price_deviation: float = 0.0
    by_period: list[dict] = field(default_factory=list)
    ai_analysis_count: int = 0
    period_days: int = 7
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TrackingSummary:
    """Summary of tracking results."""
    processed: int = 0
    ai_analyses: int = 0
    errors: int = 0
    current_price: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

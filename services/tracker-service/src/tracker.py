"""Prediction tracker for evaluating outcomes."""

import json
from datetime import datetime, timedelta
from typing import Optional

from sentilyze_core import get_logger

from .config import get_tracker_settings
from .models import PredictionOutcome, PredictionRecord, TrackingSummary

logger = get_logger(__name__)
settings = get_tracker_settings()


class PredictionTracker:
    """Tracks prediction outcomes and calculates accuracy."""

    def __init__(self):
        self.price_cache: dict[str, tuple[float, datetime]] = {}

    def calculate_outcome(
        self,
        prediction: PredictionRecord,
        actual_price: float,
    ) -> PredictionOutcome:
        """Calculate outcome for a prediction."""
        
        predicted_price = prediction.predicted_price
        predicted_direction = prediction.predicted_direction
        
        # Price difference
        price_diff = abs(actual_price - predicted_price)
        percent_diff = (price_diff / predicted_price) * 100
        
        # Actual direction
        current_price = prediction.current_price
        price_change = actual_price - current_price
        
        if price_change > settings.price_tolerance_flat:
            actual_direction = "UP"
        elif price_change < -settings.price_tolerance_flat:
            actual_direction = "DOWN"
        else:
            actual_direction = "FLAT"
        
        # Direction correct?
        direction_correct = (predicted_direction == actual_direction)
        
        # Success level
        if direction_correct and price_diff < settings.success_threshold_excellent:
            success_level = "EXCELLENT"
        elif direction_correct and price_diff < settings.success_threshold_good:
            success_level = "GOOD"
        elif direction_correct:
            success_level = "ACCEPTABLE"
        else:
            success_level = "FAILED"
        
        # Generate learning insights
        learning_insights = []
        if not direction_correct:
            learning_insights.append("Direction prediction failed - market conditions changed")
        if price_diff > settings.success_threshold_good:
            learning_insights.append("High price deviation - volatility not captured")
        if prediction.confidence_score < 50:
            learning_insights.append("Low confidence prediction - more data needed")
        
        return PredictionOutcome(
            outcome_id=f"outcome_{prediction.prediction_id}",
            prediction_id=prediction.prediction_id,
            actual_price=round(actual_price, 2),
            actual_direction=actual_direction,
            price_diff=round(price_diff, 2),
            percent_diff=round(percent_diff, 2),
            direction_correct=direction_correct,
            success_level=success_level,
            learning_insights=learning_insights,
        )

    def should_generate_ai_analysis(
        self,
        prediction: PredictionRecord,
        outcome: PredictionOutcome,
    ) -> bool:
        """Determine if AI analysis should be generated."""
        if not settings.enable_ai_analysis:
            return False
        
        # Direction error
        if settings.ai_analysis_threshold_direction_error and not outcome.direction_correct:
            return True
        
        # Large price deviation
        if outcome.price_diff > settings.ai_analysis_threshold_price_diff:
            return True
        
        return False

    def generate_ai_analysis_prompt(
        self,
        prediction: PredictionRecord,
        outcome: PredictionOutcome,
    ) -> str:
        """Generate prompt for AI analysis."""
        analysis_type = "DIRECTION ERROR" if not outcome.direction_correct else "LARGE DEVIATION"
        
        prompt = f"""
        Analyze this prediction failure for a financial market:
        
        PREDICTION:
        - Market: {prediction.market_type.upper()}
        - Symbol: {prediction.symbol}
        - Timeframe: {prediction.prediction_type}
        - Predicted Price: {prediction.predicted_price} ({prediction.predicted_direction})
        - Confidence: {prediction.confidence_score}%
        - Technical Signals: {prediction.technical_signals}
        - Sentiment: {prediction.sentiment_score}
        
        ACTUAL OUTCOME:
        - Actual Price: {outcome.actual_price} ({outcome.actual_direction})
        - Deviation: {outcome.price_diff} ({outcome.percent_diff}%)
        - Status: {analysis_type}
        
        Task:
        1. Explain why the prediction was inaccurate (2-3 sentences)
        2. Identify unexpected market factors
        3. Suggest one practical improvement
        
        Use professional, analytical tone. Maximum 150 words.
        """
        
        return prompt

    async def process_predictions(
        self,
        predictions: list[PredictionRecord],
        current_price: float,
    ) -> TrackingSummary:
        """Process a batch of predictions."""
        summary = TrackingSummary()
        summary.current_price = current_price
        
        for prediction in predictions:
            try:
                # Calculate outcome
                outcome = self.calculate_outcome(prediction, current_price)
                summary.processed += 1
                
                # AI analysis if needed
                if self.should_generate_ai_analysis(prediction, outcome):
                    # AI analysis would be generated here
                    # For now, mark as not generated
                    outcome.ai_analysis_generated = False
                    summary.ai_analyses += 1
                
            except Exception as e:
                logger.error(
                    "Error processing prediction",
                    prediction_id=prediction.prediction_id,
                    error=str(e),
                )
                summary.errors += 1
        
        return summary

    def get_price_from_cache(self, symbol: str) -> Optional[float]:
        """Get cached price if not expired."""
        if symbol in self.price_cache:
            price, timestamp = self.price_cache[symbol]
            if datetime.utcnow() - timestamp < timedelta(seconds=30):
                return price
        return None

    def cache_price(self, symbol: str, price: float) -> None:
        """Cache price with timestamp."""
        self.price_cache[symbol] = (price, datetime.utcnow())

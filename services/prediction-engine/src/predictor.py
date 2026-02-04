"""Prediction engine with technical indicators and ML."""

import os
from typing import Optional

import numpy as np

from sentilyze_core import get_logger

from .config import get_prediction_settings
from .models import TechnicalIndicators

logger = get_logger(__name__)
settings = get_prediction_settings()

# Try to import sklearn for ML
# Check if scikit-learn is available by checking environment
try:
    # Only import if ML is enabled
    if settings.enable_ml_predictions:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.preprocessing import StandardScaler
        SKLEARN_AVAILABLE = True
    else:
        SKLEARN_AVAILABLE = False
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available, ML predictions disabled")


class TechnicalAnalyzer:
    """Technical analysis for predictions."""
    
    def __init__(self):
        self.rsi_period = settings.rsi_period
        self.macd_fast = settings.macd_fast
        self.macd_slow = settings.macd_slow
        self.macd_signal = settings.macd_signal
        self.bb_period = settings.bb_period
        self.bb_std_dev = settings.bb_std_dev
        self.ema_short = settings.ema_short
        self.ema_medium = settings.ema_medium
        self.ema_long = settings.ema_long
    
    def calculate_indicators(self, prices: list[float]) -> TechnicalIndicators:
        """Calculate all technical indicators."""
        if len(prices) < 50:
            return TechnicalIndicators()
        
        indicators = TechnicalIndicators()
        prices_array = np.array(prices, dtype=np.float64)
        
        # RSI
        indicators.rsi = self._calculate_rsi(prices_array, self.rsi_period)
        
        # EMAs
        indicators.ema_short = self._calculate_ema(prices_array, self.ema_short)
        indicators.ema_medium = self._calculate_ema(prices_array, self.ema_medium)
        indicators.ema_long = self._calculate_ema(prices_array, self.ema_long)
        
        # MACD
        ema_fast = self._calculate_ema(prices_array, self.macd_fast)
        ema_slow = self._calculate_ema(prices_array, self.macd_slow)
        indicators.macd = ema_fast - ema_slow
        indicators.macd_signal = self._calculate_ema(
            np.array([indicators.macd] * len(prices_array)), 
            self.macd_signal
        )
        indicators.macd_histogram = indicators.macd - indicators.macd_signal
        
        # Bollinger Bands
        sma = np.mean(prices_array[-self.bb_period:])
        std = np.std(prices_array[-self.bb_period:])
        indicators.bb_middle = sma
        indicators.bb_upper = sma + (self.bb_std_dev * std)
        indicators.bb_lower = sma - (self.bb_std_dev * std)
        
        return indicators
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate RSI."""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calculate EMA."""
        if len(prices) < period:
            return float(prices[-1]) if len(prices) > 0 else 0.0
        
        multiplier = 2 / (period + 1)
        ema = np.mean(prices[:period])
        
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return float(ema)
    
    def calculate_technical_signal(self, indicators: TechnicalIndicators) -> float:
        """Calculate overall technical signal (-1 to 1)."""
        signals = []
        
        # RSI signal
        if indicators.rsi is not None:
            if indicators.rsi > 70:
                signals.append(-0.5)
            elif indicators.rsi < 30:
                signals.append(0.5)
            elif 40 < indicators.rsi < 60:
                signals.append(0.0)
            else:
                signals.append((indicators.rsi - 50) / 50)
        
        # MACD signal
        if indicators.macd_histogram is not None:
            if indicators.macd_histogram > 0:
                signals.append(0.3)
            else:
                signals.append(-0.3)
        
        # EMA signal
        if indicators.ema_short is not None and indicators.ema_medium is not None:
            if indicators.ema_short > indicators.ema_medium:
                signals.append(0.4)
            else:
                signals.append(-0.4)
        
        # Bollinger signal
        if indicators.bb_upper is not None and indicators.bb_lower is not None:
            bb_range = indicators.bb_upper - indicators.bb_lower
            if bb_range > 0 and indicators.bb_middle is not None:
                position = (indicators.bb_middle - indicators.bb_lower) / bb_range
                if position > 0.8:
                    signals.append(-0.3)
                elif position < 0.2:
                    signals.append(0.3)
        
        if not signals:
            return 0.0
        
        return float(np.mean(signals))


class MLPredictor:
    """ML-based price predictor using Random Forest."""
    
    def __init__(self):
        self.model: Optional[RandomForestRegressor] = None
        self.scaler: Optional[StandardScaler] = None
        self._initialized = False
        
        if SKLEARN_AVAILABLE and settings.enable_ml_predictions:
            self._init_model()
    
    def _init_model(self) -> None:
        """Initialize ML model."""
        try:
            self.model = RandomForestRegressor(
                n_estimators=settings.ml_model_estimators,
                max_depth=settings.ml_model_max_depth,
                random_state=settings.ml_model_random_state,
                n_jobs=1,
            )
            self.scaler = StandardScaler()
            self._initialized = True
            logger.info("ML model initialized")
        except Exception as e:
            logger.error(f"Failed to initialize ML model: {e}")
            self._initialized = False
    
    def predict(
        self,
        indicators: TechnicalIndicators,
        sentiment_score: float,
        current_price: float,
    ) -> float:
        """Make ML prediction."""
        if not self._initialized or not SKLEARN_AVAILABLE:
            return 0.0
        
        try:
            features = np.array([[
                indicators.rsi or 50,
                indicators.macd or 0,
                indicators.ema_short or current_price,
                indicators.ema_medium or current_price,
                sentiment_score,
            ]])
            
            prediction = self.model.predict(features)[0]
            return float(prediction)
        except Exception as e:
            logger.error(f"ML prediction failed: {e}")
            return 0.0


class PredictionEngine:
    """Main prediction engine combining technical and ML analysis."""
    
    def __init__(self):
        self.technical_analyzer = TechnicalAnalyzer()
        self.ml_predictor = MLPredictor()
    
    def generate_prediction(
        self,
        symbol: str,
        current_price: float,
        prices: list[float],
        sentiment_score: float,
        prediction_type: str,
        market_type: str = "generic",
    ) -> dict:
        """Generate price prediction."""
        
        # Calculate technical indicators
        indicators = self.technical_analyzer.calculate_indicators(prices)
        
        # Technical signal
        technical_signal = self.technical_analyzer.calculate_technical_signal(indicators)
        
        # ML prediction
        ml_prediction = 0.0
        if settings.enable_ml_predictions:
            ml_prediction = self.ml_predictor.predict(
                indicators, sentiment_score, current_price
            )
        
        # Weighted combination
        weights = settings.prediction_weights
        combined_signal = (
            technical_signal * weights["technical"] +
            sentiment_score * weights["sentiment"] +
            ml_prediction * weights["ml"]
        )
        
        # Time multiplier - Optimized for sentiment-to-price lag
        time_multipliers = {
            "1h": 1.0,    # Baseline - most balanced
            "2h": 1.3,    # Optimal trend capture
            "3h": 1.5,    # Long-term reliable
            "4h": 2.0,    # Optional extended timeframe
        }
        multiplier = time_multipliers.get(prediction_type, 1.0)
        
        # Predicted change
        predicted_change = combined_signal * 0.3 * multiplier
        predicted_price = current_price * (1 + predicted_change)
        
        # Direction
        if predicted_change > 0.05:
            direction = "UP"
        elif predicted_change < -0.05:
            direction = "DOWN"
        else:
            direction = "FLAT"
        
        # Confidence
        confidence_score = self._calculate_confidence(
            indicators, sentiment_score, prediction_type
        )
        
        confidence_level = (
            "LOW" if confidence_score < 50 
            else "MEDIUM" if confidence_score < 75 
            else "HIGH"
        )
        
        # Reasoning
        reasoning = self._generate_reasoning(indicators, sentiment_score, direction)
        
        return {
            "symbol": symbol,
            "market_type": market_type,
            "prediction_type": prediction_type,
            "current_price": round(current_price, 2),
            "predicted_price": round(predicted_price, 2),
            "predicted_direction": direction,
            "confidence_score": confidence_score,
            "confidence_level": confidence_level,
            "technical_indicators": indicators.to_dict(),
            "sentiment_score": sentiment_score,
            "reasoning": reasoning,
        }
    
    def _calculate_confidence(
        self,
        indicators: TechnicalIndicators,
        sentiment_score: float,
        prediction_type: str,
    ) -> int:
        """Calculate confidence score (0-100)."""
        confidence = 40  # Base confidence
        
        # Technical indicator presence
        if indicators.rsi is not None:
            confidence += 10
        if indicators.macd is not None:
            confidence += 10
        if all([indicators.ema_short, indicators.ema_medium, indicators.ema_long]):
            confidence += 10
        
        # Signal alignment
        signals = []
        if indicators.rsi is not None:
            signals.append(1 if indicators.rsi > 50 else -1)
        if indicators.macd_histogram is not None:
            signals.append(1 if indicators.macd_histogram > 0 else -1)
        if indicators.ema_short is not None and indicators.ema_medium is not None:
            signals.append(1 if indicators.ema_short > indicators.ema_medium else -1)
        
        if signals and len(set(signals)) == 1:
            confidence += 15
        
        # Sentiment strength
        confidence += min(15, abs(sentiment_score) * 30)
        
        # Time penalty - Optimized confidence scoring
        time_penalties = {
            "1h": 0,      # Most reliable
            "2h": -3,     # Minimal penalty
            "3h": -8,     # Moderate penalty
            "4h": -12,    # Higher uncertainty
        }
        confidence += time_penalties.get(prediction_type, 0)
        
        return max(settings.min_confidence_score, min(settings.max_confidence_score, confidence))
    
    def _generate_reasoning(
        self,
        indicators: TechnicalIndicators,
        sentiment_score: float,
        direction: str,
    ) -> str:
        """Generate prediction reasoning."""
        reasons = []
        
        if indicators.rsi is not None:
            if indicators.rsi > 70:
                reasons.append(f"RSI {indicators.rsi:.1f} indicates overbought conditions")
            elif indicators.rsi < 30:
                reasons.append(f"RSI {indicators.rsi:.1f} indicates oversold conditions")
            else:
                reasons.append(f"RSI {indicators.rsi:.1f} is in neutral territory")
        
        if indicators.macd_histogram is not None:
            if indicators.macd_histogram > 0:
                reasons.append("MACD histogram positive (upward momentum)")
            else:
                reasons.append("MACD histogram negative (downward momentum)")
        
        if indicators.ema_short is not None and indicators.ema_medium is not None:
            if indicators.ema_short > indicators.ema_medium:
                reasons.append("Short-term EMA above medium-term EMA (bullish signal)")
            else:
                reasons.append("Short-term EMA below medium-term EMA (bearish signal)")
        
        if abs(sentiment_score) > 0.3:
            sentiment_desc = "positive" if sentiment_score > 0 else "negative"
            reasons.append(f"Market sentiment is {sentiment_desc} ({sentiment_score:.2f})")
        
        if not reasons:
            reasons.append("Technical indicators show mixed signals")
        
        return "; ".join(reasons)

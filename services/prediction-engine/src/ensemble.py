"""Ensemble predictor combining LSTM, ARIMA, XGBoost, and Random Forest.

The ensemble predictor aggregates predictions from multiple models to produce
more accurate and reliable forecasts.

Ensemble Strategy:
- LSTM: 35% weight (deep learning, captures complex patterns)
- XGBoost: 25% weight (gradient boosting, feature importance)
- Random Forest: 20% weight (baseline, stable)
- ARIMA: 20% weight (classical time series, trend capture)

Confidence Scoring:
- HIGH: Models agree within 2% (consensus)
- MEDIUM: Models agree within 5%
- LOW: Models diverge > 5%
"""

from typing import Optional, TYPE_CHECKING

import numpy as np

from sentilyze_core import get_logger

from .models import ARIMAPredictor, LSTMPredictor, XGBoostPredictor
from .predictor import MLPredictor

if TYPE_CHECKING:
    from .models import TechnicalIndicators

logger = get_logger(__name__)


class EnsemblePredictor:
    """Ensemble predictor combining multiple ML models."""

    def __init__(
        self,
        weights: Optional[dict[str, float]] = None,
        enable_lstm: bool = True,
        enable_arima: bool = True,
        enable_xgboost: bool = True,
        enable_random_forest: bool = True,
    ):
        """Initialize ensemble predictor.

        Args:
            weights: Model weights dict (default: LSTM=0.35, XGBoost=0.25, RF=0.20, ARIMA=0.20)
            enable_lstm: Enable LSTM model
            enable_arima: Enable ARIMA model
            enable_xgboost: Enable XGBoost model
            enable_random_forest: Enable Random Forest model
        """
        # Default weights
        self.weights = weights or {
            'lstm': 0.35,
            'xgboost': 0.25,
            'random_forest': 0.20,
            'arima': 0.20,
        }

        # Normalize weights
        total_weight = sum(self.weights.values())
        self.weights = {k: v / total_weight for k, v in self.weights.items()}

        # Initialize models
        self.lstm = LSTMPredictor() if enable_lstm else None
        self.arima = ARIMAPredictor() if enable_arima else None
        self.xgboost = XGBoostPredictor() if enable_xgboost else None
        self.random_forest = MLPredictor() if enable_random_forest else None

        self.enable_lstm = enable_lstm and self.lstm is not None
        self.enable_arima = enable_arima and self.arima is not None
        self.enable_xgboost = enable_xgboost and self.xgboost is not None
        self.enable_random_forest = enable_random_forest and self.random_forest is not None

        logger.info(
            "Ensemble predictor initialized",
            models={
                'lstm': self.enable_lstm,
                'arima': self.enable_arima,
                'xgboost': self.enable_xgboost,
                'random_forest': self.enable_random_forest,
            },
            weights=self.weights,
        )

    async def predict(
        self,
        # Technical indicators
        indicators: 'TechnicalIndicators',
        sentiment_score: float,
        current_price: float,

        # Economic data
        economic_data: Optional[dict] = None,

        # Historical data for LSTM/ARIMA
        price_history: Optional[np.ndarray] = None,
        feature_history: Optional[np.ndarray] = None,
    ) -> dict:
        """Generate ensemble prediction.

        Args:
            indicators: Technical indicators
            sentiment_score: Sentiment score (-1 to 1)
            current_price: Current gold price
            economic_data: Economic indicators dict
            price_history: Historical prices (for ARIMA)
            feature_history: Historical features (for LSTM)

        Returns:
            Ensemble prediction dict with individual model predictions
        """
        predictions = {}
        valid_weights = {}

        # 1. Random Forest prediction (baseline)
        if self.enable_random_forest and self.random_forest is not None:
            try:
                rf_signal = await self.random_forest.predict(
                    indicators=indicators,
                    sentiment_score=sentiment_score,
                    current_price=current_price,
                    economic_data=economic_data,
                )
                predictions['random_forest'] = rf_signal
                valid_weights['random_forest'] = self.weights.get('random_forest', 0.20)

                logger.debug("Random Forest prediction", signal=rf_signal)
            except Exception as e:
                logger.error(f"Random Forest prediction failed: {e}")

        # 2. XGBoost prediction
        if self.enable_xgboost and self.xgboost is not None:
            try:
                # Build feature vector (same as Random Forest but for XGBoost)
                features = self._build_feature_vector(
                    indicators, sentiment_score, economic_data
                )

                xgb_signal = await self.xgboost.predict(
                    features=features,
                    current_price=current_price,
                )
                predictions['xgboost'] = xgb_signal
                valid_weights['xgboost'] = self.weights.get('xgboost', 0.25)

                logger.debug("XGBoost prediction", signal=xgb_signal)
            except Exception as e:
                logger.error(f"XGBoost prediction failed: {e}")

        # 3. LSTM prediction (if feature history available)
        if self.enable_lstm and self.lstm is not None and feature_history is not None:
            try:
                lstm_signal = await self.lstm.predict(
                    recent_data=feature_history,
                    current_price=current_price,
                )
                predictions['lstm'] = lstm_signal
                valid_weights['lstm'] = self.weights.get('lstm', 0.35)

                logger.debug("LSTM prediction", signal=lstm_signal)
            except Exception as e:
                logger.error(f"LSTM prediction failed: {e}")

        # 4. ARIMA prediction (if price history available)
        if self.enable_arima and self.arima is not None and price_history is not None:
            try:
                arima_signal = await self.arima.predict(
                    prices=price_history,
                    current_price=current_price,
                    steps=1,
                )
                predictions['arima'] = arima_signal
                valid_weights['arima'] = self.weights.get('arima', 0.20)

                logger.debug("ARIMA prediction", signal=arima_signal)
            except Exception as e:
                logger.error(f"ARIMA prediction failed: {e}")

        # 5. Calculate ensemble prediction
        if not predictions:
            logger.warning("No model predictions available")
            return {
                'ensemble_signal': 0.0,
                'ensemble_price': current_price,
                'confidence': 'LOW',
                'models': {},
                'weights_used': {},
            }

        # Normalize weights for available models only
        total_weight = sum(valid_weights.values())
        normalized_weights = {k: v / total_weight for k, v in valid_weights.items()}

        # Weighted average
        ensemble_signal = sum(
            predictions[model] * normalized_weights[model]
            for model in predictions
        )

        # Calculate predicted price
        price_change_percent = ensemble_signal * 0.03  # Convert signal to % change
        ensemble_price = current_price * (1 + price_change_percent)

        # Calculate confidence based on model agreement
        confidence = self._calculate_confidence(predictions)

        result = {
            'ensemble_signal': float(ensemble_signal),
            'ensemble_price': float(ensemble_price),
            'change_percent': float(price_change_percent * 100),
            'confidence': confidence,
            'models': {k: float(v) for k, v in predictions.items()},
            'weights_used': normalized_weights,
            'num_models': len(predictions),
        }

        logger.info(
            "Ensemble prediction complete",
            signal=ensemble_signal,
            price=ensemble_price,
            confidence=confidence,
            models=list(predictions.keys()),
        )

        return result

    def _build_feature_vector(
        self,
        indicators: 'TechnicalIndicators',
        sentiment_score: float,
        economic_data: Optional[dict],
    ) -> np.ndarray:
        """Build 15-feature vector for XGBoost.

        Returns:
            Feature vector (15,)
        """
        # Default economic data
        if economic_data is None:
            economic_data = {}

        dxy = economic_data.get('dxy', 100) / 100.0
        treasury = economic_data.get('treasury_10y', 3.0) / 5.0
        cpi = economic_data.get('cpi', 300) / 300.0
        oil = economic_data.get('wti_oil', 70) / 100.0
        vix = economic_data.get('vix', 15) / 30.0
        sp500 = economic_data.get('sp500', 4500) / 5000.0

        ema_short = indicators.ema_short or 0
        ema_medium = indicators.ema_medium or 0

        features = np.array([
            # Technical (5)
            indicators.rsi or 50,
            indicators.macd or 0,
            ema_short,
            ema_medium,
            sentiment_score,

            # Economic (6)
            dxy,
            treasury,
            cpi,
            oil,
            vix,
            sp500,

            # Derived (4)
            ema_short - ema_medium,
            dxy * treasury,
            vix / (sp500 + 0.01),
            cpi * oil,
        ])

        return features

    def _calculate_confidence(self, predictions: dict[str, float]) -> str:
        """Calculate confidence based on model agreement.

        Args:
            predictions: Dict of model predictions

        Returns:
            Confidence level: HIGH, MEDIUM, or LOW
        """
        if len(predictions) < 2:
            return 'LOW'

        signals = list(predictions.values())
        std_dev = np.std(signals)
        mean_signal = np.mean(signals)

        # Calculate coefficient of variation
        if abs(mean_signal) > 0.01:
            cv = std_dev / abs(mean_signal)
        else:
            cv = std_dev

        # Confidence thresholds
        if std_dev < 0.1 or cv < 0.3:
            return 'HIGH'  # Models agree closely
        elif std_dev < 0.2 or cv < 0.6:
            return 'MEDIUM'  # Moderate agreement
        else:
            return 'LOW'  # Models diverge

    def get_model_info(self) -> dict:
        """Get information about ensemble models."""
        info = {
            'ensemble_weights': self.weights,
            'models_enabled': {
                'lstm': self.enable_lstm,
                'arima': self.enable_arima,
                'xgboost': self.enable_xgboost,
                'random_forest': self.enable_random_forest,
            },
        }

        # Get individual model info
        if self.lstm:
            info['lstm_info'] = self.lstm.get_model_info()
        if self.arima:
            info['arima_info'] = self.arima.get_model_info()
        if self.xgboost:
            info['xgboost_info'] = self.xgboost.get_model_info()

        return info

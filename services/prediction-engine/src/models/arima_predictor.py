"""ARIMA-based predictor for short-term gold price forecasting.

ARIMA (AutoRegressive Integrated Moving Average) is a classical time series
model ideal for short-term predictions (1-7 days).

Key Features:
- Auto-tuning with auto_arima for optimal (p,d,q) parameters
- Handles trend and seasonality
- Fast inference
- Good for 1-7 day predictions
"""

from typing import Optional, Tuple

import numpy as np

from sentilyze_core import get_logger

logger = get_logger(__name__)

# Check statsmodels/pmdarima availability
try:
    from statsmodels.tsa.arima.model import ARIMA
    import pmdarima as pm

    ARIMA_AVAILABLE = True
    logger.info("ARIMA models available")
except ImportError:
    ARIMA_AVAILABLE = False
    logger.warning("statsmodels/pmdarima not available, ARIMA predictor disabled")


class ARIMAPredictor:
    """ARIMA-based price predictor for short-term forecasting.

    Uses auto_arima for automatic parameter selection (p, d, q).
    Best for 1-7 day predictions.
    """

    def __init__(
        self,
        seasonal: bool = False,
        m: int = 7,  # Weekly seasonality
        max_p: int = 5,
        max_d: int = 2,
        max_q: int = 5,
    ):
        """Initialize ARIMA predictor.

        Args:
            seasonal: Enable seasonal ARIMA (SARIMA)
            m: Seasonal period (default: 7 for weekly)
            max_p: Max AR order
            max_d: Max differencing order
            max_q: Max MA order
        """
        self.seasonal = seasonal
        self.m = m
        self.max_p = max_p
        self.max_d = max_d
        self.max_q = max_q

        self.model: Optional[ARIMA] = None
        self.fitted_model = None
        self.order: Optional[Tuple[int, int, int]] = None
        self._initialized = False

        if not ARIMA_AVAILABLE:
            logger.error("statsmodels/pmdarima not available, cannot initialize ARIMA")

    async def auto_fit(
        self,
        prices: np.ndarray,
        test_size: int = 7,
    ) -> dict:
        """Auto-fit ARIMA model with optimal parameters.

        Args:
            prices: Historical price data (1D array)
            test_size: Number of samples for test set

        Returns:
            Fitting results dict
        """
        if not ARIMA_AVAILABLE:
            raise RuntimeError("ARIMA not available")

        try:
            logger.info(
                "Auto-fitting ARIMA model",
                samples=len(prices),
                seasonal=self.seasonal,
            )

            # Split train/test
            train = prices[:-test_size] if test_size > 0 else prices
            test = prices[-test_size:] if test_size > 0 else None

            # Auto ARIMA
            model = pm.auto_arima(
                train,
                start_p=1,
                start_q=1,
                max_p=self.max_p,
                max_d=self.max_d,
                max_q=self.max_q,
                seasonal=self.seasonal,
                m=self.m if self.seasonal else 1,
                stepwise=True,
                suppress_warnings=True,
                error_action='ignore',
                trace=False,
            )

            self.fitted_model = model
            self.order = model.order
            self._initialized = True

            logger.info(
                "ARIMA model fitted",
                order=self.order,
                aic=model.aic(),
                bic=model.bic(),
            )

            # Evaluate on test set if available
            results = {
                'order': self.order,
                'aic': float(model.aic()),
                'bic': float(model.bic()),
            }

            if test is not None and len(test) > 0:
                predictions = model.predict(n_periods=len(test))
                mae = np.mean(np.abs(test - predictions))
                mape = np.mean(np.abs((test - predictions) / test)) * 100

                results['test_mae'] = float(mae)
                results['test_mape'] = float(mape)

                logger.info("ARIMA test metrics", mae=mae, mape=mape)

            return results

        except Exception as e:
            logger.error(f"ARIMA auto-fit failed: {e}")
            raise

    async def train(
        self,
        prices: np.ndarray,
        order: Optional[Tuple[int, int, int]] = None,
    ) -> dict:
        """Train ARIMA model with specified or auto-tuned order.

        Args:
            prices: Historical price data
            order: Manual (p, d, q) order (optional, uses auto_arima if None)

        Returns:
            Training results
        """
        if not ARIMA_AVAILABLE:
            raise RuntimeError("ARIMA not available")

        try:
            if order is None:
                # Auto-tune
                return await self.auto_fit(prices)

            # Manual order
            self.order = order
            model = ARIMA(prices, order=order)
            self.fitted_model = model.fit()
            self._initialized = True

            logger.info(
                "ARIMA model trained",
                order=order,
                aic=self.fitted_model.aic,
                bic=self.fitted_model.bic,
            )

            return {
                'order': order,
                'aic': float(self.fitted_model.aic),
                'bic': float(self.fitted_model.bic),
            }

        except Exception as e:
            logger.error(f"ARIMA training failed: {e}")
            raise

    async def predict(
        self,
        prices: np.ndarray,
        current_price: float,
        steps: int = 1,
    ) -> float:
        """Make price prediction using ARIMA.

        Args:
            prices: Recent historical prices
            current_price: Current price
            steps: Number of steps ahead to predict (default: 1)

        Returns:
            Predicted price change signal (-1 to 1)
        """
        if not self._initialized or self.fitted_model is None:
            logger.warning("ARIMA model not initialized, returning 0")
            return 0.0

        try:
            # Update model with recent data
            if len(prices) > 100:
                prices = prices[-100:]  # Use last 100 samples

            # Refit with recent data (fast)
            model = pm.auto_arima(
                prices,
                start_p=self.order[0],
                start_q=self.order[2],
                max_p=self.order[0] + 1,
                max_d=self.order[1],
                max_q=self.order[2] + 1,
                seasonal=self.seasonal,
                m=self.m if self.seasonal else 1,
                stepwise=True,
                suppress_warnings=True,
                error_action='ignore',
            )

            # Forecast
            forecast = model.predict(n_periods=steps)
            predicted_price = forecast[-1]

            # Calculate change signal
            price_change = (predicted_price - current_price) / current_price
            signal = np.clip(price_change * 10, -1, 1)

            logger.debug(
                "ARIMA prediction",
                current_price=current_price,
                predicted_price=predicted_price,
                signal=signal,
                steps=steps,
            )

            return float(signal)

        except Exception as e:
            logger.error(f"ARIMA prediction failed: {e}")
            return 0.0

    def get_model_info(self) -> dict:
        """Get model information."""
        return {
            'model_type': 'ARIMA',
            'initialized': self._initialized,
            'arima_available': ARIMA_AVAILABLE,
            'order': self.order,
            'seasonal': self.seasonal,
            'aic': float(self.fitted_model.aic) if self.fitted_model and hasattr(self.fitted_model, 'aic') else None,
            'bic': float(self.fitted_model.bic) if self.fitted_model and hasattr(self.fitted_model, 'bic') else None,
        }

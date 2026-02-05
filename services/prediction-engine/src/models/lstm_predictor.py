"""LSTM-based predictor for multivariate time series gold price prediction.

This model uses Long Short-Term Memory (LSTM) neural networks to predict
gold prices based on historical price data and economic indicators.

Key Features:
- Multivariate time series (price + economic features)
- 30-day lookback window
- Handles missing data gracefully
- Normalization for stable training
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Tuple

import numpy as np

from sentilyze_core import get_logger

logger = get_logger(__name__)

# Check TensorFlow availability
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers
    from sklearn.preprocessing import MinMaxScaler

    TF_AVAILABLE = True
    logger.info("TensorFlow available for LSTM model")
except ImportError:
    TF_AVAILABLE = False
    logger.warning("TensorFlow not available, LSTM predictor disabled")


class LSTMPredictor:
    """LSTM-based price predictor with economic features.

    Architecture:
    - Input: (lookback_window, num_features)
    - LSTM(64) -> Dropout(0.2) -> LSTM(32) -> Dense(1)

    Features:
    - gold_price, dxy, treasury_10y, cpi, wti_oil, vix, sp500
    - rsi, macd, ema_short (technical indicators)
    """

    def __init__(
        self,
        lookback_window: int = 30,
        num_features: int = 10,
        model_path: Optional[str] = None,
    ):
        """Initialize LSTM predictor.

        Args:
            lookback_window: Number of days to look back (default: 30)
            num_features: Number of input features (default: 10)
            model_path: Path to saved model (optional)
        """
        self.lookback_window = lookback_window
        self.num_features = num_features
        self.model_path = model_path or "models/lstm_gold_predictor.keras"

        self.model: Optional[keras.Model] = None
        self.scaler: Optional[MinMaxScaler] = None
        self._initialized = False

        if not TF_AVAILABLE:
            logger.error("TensorFlow not available, cannot initialize LSTM")
            return

        # Initialize or load model
        if os.path.exists(self.model_path):
            self._load_model()
        else:
            self._build_model()

    def _build_model(self) -> None:
        """Build LSTM model architecture."""
        if not TF_AVAILABLE:
            return

        try:
            # Input layer
            inputs = layers.Input(shape=(self.lookback_window, self.num_features))

            # LSTM layers
            x = layers.LSTM(64, return_sequences=True)(inputs)
            x = layers.Dropout(0.2)(x)
            x = layers.LSTM(32)(x)
            x = layers.Dropout(0.2)(x)

            # Dense output
            outputs = layers.Dense(1)(x)

            # Compile model
            self.model = keras.Model(inputs=inputs, outputs=outputs)
            self.model.compile(
                optimizer=keras.optimizers.Adam(learning_rate=0.001),
                loss='mse',
                metrics=['mae']
            )

            # Initialize scaler
            self.scaler = MinMaxScaler(feature_range=(0, 1))

            self._initialized = True
            logger.info("LSTM model built successfully", architecture=self.model.summary())

        except Exception as e:
            logger.error(f"Failed to build LSTM model: {e}")
            self._initialized = False

    def _load_model(self) -> None:
        """Load pre-trained model from disk."""
        if not TF_AVAILABLE:
            return

        try:
            self.model = keras.models.load_model(self.model_path)
            self.scaler = MinMaxScaler(feature_range=(0, 1))
            self._initialized = True
            logger.info("LSTM model loaded", path=self.model_path)
        except Exception as e:
            logger.error(f"Failed to load LSTM model: {e}")
            self._build_model()

    def save_model(self, path: Optional[str] = None) -> None:
        """Save model to disk."""
        if not self._initialized or self.model is None:
            logger.warning("No model to save")
            return

        save_path = path or self.model_path
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            self.model.save(save_path)
            logger.info("LSTM model saved", path=save_path)
        except Exception as e:
            logger.error(f"Failed to save model: {e}")

    def prepare_sequences(
        self,
        data: np.ndarray,
        lookback: Optional[int] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare sequences for LSTM training/prediction.

        Args:
            data: Input data (n_samples, n_features)
            lookback: Lookback window (default: self.lookback_window)

        Returns:
            X: Input sequences (n_sequences, lookback, n_features)
            y: Target values (n_sequences,)
        """
        lookback = lookback or self.lookback_window

        X, y = [], []
        for i in range(lookback, len(data)):
            X.append(data[i - lookback:i])
            y.append(data[i, 0])  # Assuming first column is target (gold price)

        return np.array(X), np.array(y)

    async def train(
        self,
        training_data: np.ndarray,
        epochs: int = 50,
        batch_size: int = 32,
        validation_split: float = 0.2,
    ) -> dict:
        """Train LSTM model on historical data.

        Args:
            training_data: Historical data (n_samples, n_features)
                          Columns: [gold_price, dxy, treasury, cpi, oil, vix, sp500, rsi, macd, ema]
            epochs: Number of training epochs
            batch_size: Batch size
            validation_split: Validation data ratio

        Returns:
            Training history dict
        """
        if not self._initialized or self.model is None:
            raise RuntimeError("Model not initialized")

        try:
            # Normalize data
            scaled_data = self.scaler.fit_transform(training_data)

            # Prepare sequences
            X, y = self.prepare_sequences(scaled_data)

            logger.info(
                "Training LSTM model",
                sequences=len(X),
                lookback=self.lookback_window,
                features=self.num_features,
                epochs=epochs,
            )

            # Train model
            history = self.model.fit(
                X, y,
                epochs=epochs,
                batch_size=batch_size,
                validation_split=validation_split,
                callbacks=[
                    keras.callbacks.EarlyStopping(
                        monitor='val_loss',
                        patience=10,
                        restore_best_weights=True,
                    ),
                    keras.callbacks.ReduceLROnPlateau(
                        monitor='val_loss',
                        factor=0.5,
                        patience=5,
                        min_lr=0.00001,
                    ),
                ],
                verbose=1,
            )

            # Save model
            self.save_model()

            return {
                'final_loss': float(history.history['loss'][-1]),
                'final_val_loss': float(history.history['val_loss'][-1]),
                'final_mae': float(history.history['mae'][-1]),
                'final_val_mae': float(history.history['val_mae'][-1]),
                'epochs_trained': len(history.history['loss']),
            }

        except Exception as e:
            logger.error(f"LSTM training failed: {e}")
            raise

    async def predict(
        self,
        recent_data: np.ndarray,
        current_price: float,
    ) -> float:
        """Make price prediction using LSTM.

        Args:
            recent_data: Recent historical data (lookback_window, n_features)
            current_price: Current gold price (for denormalization)

        Returns:
            Predicted price change signal (-1 to 1)
        """
        if not self._initialized or self.model is None:
            logger.warning("LSTM model not initialized, returning 0")
            return 0.0

        try:
            # Handle insufficient data
            if len(recent_data) < self.lookback_window:
                logger.warning(
                    "Insufficient data for LSTM prediction",
                    available=len(recent_data),
                    required=self.lookback_window,
                )
                return 0.0

            # Take last lookback_window samples
            recent_data = recent_data[-self.lookback_window:]

            # Normalize
            scaled_data = self.scaler.transform(recent_data)

            # Reshape for model input
            X = scaled_data.reshape(1, self.lookback_window, self.num_features)

            # Predict
            prediction_scaled = self.model.predict(X, verbose=0)[0][0]

            # Denormalize prediction
            # Assuming first feature is gold price
            predicted_price = self.scaler.inverse_transform(
                np.array([[prediction_scaled] + [0] * (self.num_features - 1)])
            )[0][0]

            # Calculate change signal (-1 to 1)
            price_change = (predicted_price - current_price) / current_price
            signal = np.clip(price_change * 10, -1, 1)  # Scale to [-1, 1]

            logger.debug(
                "LSTM prediction",
                current_price=current_price,
                predicted_price=predicted_price,
                signal=signal,
            )

            return float(signal)

        except Exception as e:
            logger.error(f"LSTM prediction failed: {e}")
            return 0.0

    def get_model_info(self) -> dict:
        """Get model information."""
        return {
            'model_type': 'LSTM',
            'initialized': self._initialized,
            'tensorflow_available': TF_AVAILABLE,
            'lookback_window': self.lookback_window,
            'num_features': self.num_features,
            'model_path': self.model_path,
            'trainable_params': self.model.count_params() if self.model else 0,
        }

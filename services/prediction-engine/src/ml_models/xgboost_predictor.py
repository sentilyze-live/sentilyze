"""XGBoost-based predictor for gold price prediction with feature importance.

XGBoost (eXtreme Gradient Boosting) is a powerful machine learning algorithm
that performs well with structured/tabular data.

Key Features:
- Feature importance analysis
- Handles missing values
- Fast training and inference
- Hyperparameter tuning support
- Regularization to prevent overfitting
"""

from typing import Optional

import numpy as np

from sentilyze_core import get_logger

logger = get_logger(__name__)

# Check XGBoost availability
try:
    import xgboost as xgb
    from sklearn.preprocessing import StandardScaler

    XGBOOST_AVAILABLE = True
    logger.info("XGBoost available")
except ImportError:
    XGBOOST_AVAILABLE = False
    logger.warning("XGBoost not available, XGBoost predictor disabled")


class XGBoostPredictor:
    """XGBoost-based price predictor with feature importance.

    Features (15 total):
    - Technical: RSI, MACD, EMA short, EMA medium, sentiment
    - Economic: DXY, Treasury 10Y, CPI, Oil, VIX, S&P 500
    - Derived: EMA spread, USD-interest, fear-equity ratio, inflation-energy
    """

    def __init__(
        self,
        n_estimators: int = 200,
        max_depth: int = 6,
        learning_rate: float = 0.1,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        model_path: Optional[str] = None,
    ):
        """Initialize XGBoost predictor.

        Args:
            n_estimators: Number of boosting rounds (trees)
            max_depth: Maximum tree depth
            learning_rate: Learning rate (eta)
            subsample: Subsample ratio of training data
            colsample_bytree: Subsample ratio of features
            model_path: Path to saved model (optional)
        """
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.model_path = model_path or "models/xgboost_gold_predictor.json"

        self.model: Optional[xgb.XGBRegressor] = None
        self.scaler: Optional[StandardScaler] = None
        self.feature_names: list[str] = [
            # Technical (5)
            'rsi', 'macd', 'ema_short', 'ema_medium', 'sentiment_score',
            # Economic (6)
            'dxy', 'treasury_10y', 'cpi', 'wti_oil', 'vix', 'sp500',
            # Derived (4)
            'ema_spread', 'usd_interest', 'fear_equity_ratio', 'inflation_energy',
        ]
        self.feature_importances_: Optional[dict] = None
        self._initialized = False

        if not XGBOOST_AVAILABLE:
            logger.error("XGBoost not available, cannot initialize")
            return

        self._build_model()

    def _build_model(self) -> None:
        """Build XGBoost model."""
        if not XGBOOST_AVAILABLE:
            return

        try:
            self.model = xgb.XGBRegressor(
                n_estimators=self.n_estimators,
                max_depth=self.max_depth,
                learning_rate=self.learning_rate,
                subsample=self.subsample,
                colsample_bytree=self.colsample_bytree,
                objective='reg:squarederror',
                random_state=42,
                n_jobs=-1,
            )

            self.scaler = StandardScaler()
            self._initialized = True

            logger.info(
                "XGBoost model built",
                n_estimators=self.n_estimators,
                max_depth=self.max_depth,
                learning_rate=self.learning_rate,
            )

        except Exception as e:
            logger.error(f"Failed to build XGBoost model: {e}")
            self._initialized = False

    def load_model(self, path: Optional[str] = None) -> None:
        """Load pre-trained model from disk."""
        if not XGBOOST_AVAILABLE:
            return

        load_path = path or self.model_path

        try:
            self.model = xgb.XGBRegressor()
            self.model.load_model(load_path)
            self.scaler = StandardScaler()
            self._initialized = True

            logger.info("XGBoost model loaded", path=load_path)
        except Exception as e:
            logger.error(f"Failed to load XGBoost model: {e}")
            self._build_model()

    def save_model(self, path: Optional[str] = None) -> None:
        """Save model to disk."""
        if not self._initialized or self.model is None:
            logger.warning("No model to save")
            return

        save_path = path or self.model_path

        try:
            import os
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            self.model.save_model(save_path)
            logger.info("XGBoost model saved", path=save_path)
        except Exception as e:
            logger.error(f"Failed to save model: {e}")

    async def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        early_stopping_rounds: int = 20,
    ) -> dict:
        """Train XGBoost model.

        Args:
            X_train: Training features (n_samples, n_features)
            y_train: Training targets (n_samples,)
            X_val: Validation features (optional)
            y_val: Validation targets (optional)
            early_stopping_rounds: Early stopping rounds

        Returns:
            Training results dict
        """
        if not self._initialized or self.model is None:
            raise RuntimeError("Model not initialized")

        try:
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)

            eval_set = None
            if X_val is not None and y_val is not None:
                X_val_scaled = self.scaler.transform(X_val)
                eval_set = [(X_val_scaled, y_val)]

            logger.info(
                "Training XGBoost model",
                samples=len(X_train),
                features=X_train.shape[1],
                val_samples=len(X_val) if X_val is not None else 0,
            )

            # Train model
            self.model.fit(
                X_train_scaled,
                y_train,
                eval_set=eval_set,
                early_stopping_rounds=early_stopping_rounds if eval_set else None,
                verbose=False,
            )

            # Extract feature importances
            self._extract_feature_importances()

            # Save model
            self.save_model()

            # Calculate metrics
            train_pred = self.model.predict(X_train_scaled)
            train_mae = np.mean(np.abs(y_train - train_pred))
            train_rmse = np.sqrt(np.mean((y_train - train_pred) ** 2))

            results = {
                'train_mae': float(train_mae),
                'train_rmse': float(train_rmse),
                'n_estimators': self.model.get_booster().num_boosted_rounds(),
            }

            if eval_set:
                val_pred = self.model.predict(X_val_scaled)
                val_mae = np.mean(np.abs(y_val - val_pred))
                val_rmse = np.sqrt(np.mean((y_val - val_pred) ** 2))

                results['val_mae'] = float(val_mae)
                results['val_rmse'] = float(val_rmse)

                logger.info("XGBoost validation metrics", val_mae=val_mae, val_rmse=val_rmse)

            logger.info("XGBoost training complete", results=results)
            return results

        except Exception as e:
            logger.error(f"XGBoost training failed: {e}")
            raise

    def _extract_feature_importances(self) -> None:
        """Extract and sort feature importances."""
        if self.model is None:
            return

        try:
            importances = self.model.feature_importances_

            # Create dict with feature names
            self.feature_importances_ = {
                name: float(imp)
                for name, imp in zip(self.feature_names, importances)
            }

            # Sort by importance
            self.feature_importances_ = dict(
                sorted(self.feature_importances_.items(), key=lambda x: x[1], reverse=True)
            )

            logger.info("Feature importances extracted", top_3=list(self.feature_importances_.items())[:3])

        except Exception as e:
            logger.error(f"Failed to extract feature importances: {e}")

    async def predict(
        self,
        features: np.ndarray,
        current_price: float,
    ) -> float:
        """Make price prediction using XGBoost.

        Args:
            features: Feature vector (15 features)
            current_price: Current gold price

        Returns:
            Predicted price change signal (-1 to 1)
        """
        if not self._initialized or self.model is None:
            logger.warning("XGBoost model not initialized, returning 0")
            return 0.0

        try:
            # Scale features
            features_scaled = self.scaler.transform(features.reshape(1, -1))

            # Predict
            prediction = self.model.predict(features_scaled)[0]

            # Convert to signal (-1 to 1)
            # Prediction is expected to be price change
            signal = np.clip(prediction, -1, 1)

            logger.debug(
                "XGBoost prediction",
                current_price=current_price,
                signal=signal,
            )

            return float(signal)

        except Exception as e:
            logger.error(f"XGBoost prediction failed: {e}")
            return 0.0

    def get_feature_importance(self) -> dict:
        """Get feature importance ranking.

        Returns:
            Dict of {feature_name: importance_score} sorted by importance
        """
        if self.feature_importances_ is None:
            self._extract_feature_importances()

        return self.feature_importances_ or {}

    def get_model_info(self) -> dict:
        """Get model information."""
        return {
            'model_type': 'XGBoost',
            'initialized': self._initialized,
            'xgboost_available': XGBOOST_AVAILABLE,
            'n_estimators': self.n_estimators,
            'max_depth': self.max_depth,
            'learning_rate': self.learning_rate,
            'num_features': len(self.feature_names),
            'top_features': list(self.get_feature_importance().items())[:5] if self.feature_importances_ else None,
        }

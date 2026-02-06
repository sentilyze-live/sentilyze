"""Model training pipeline.

Orchestrates training of all ML models (LSTM, XGBoost, Random Forest, ARIMA)
using historical data from BigQuery. Supports walk-forward cross-validation
and saves trained models to Google Cloud Storage.
"""

import os
import json
import tempfile
from datetime import datetime
from typing import Optional

import numpy as np

from sentilyze_core import get_logger, get_settings

from .data_loader import TrainingDataLoader

logger = get_logger(__name__)
settings = get_settings()


class TrainingPipeline:
    """Orchestrate training of all prediction models."""

    def __init__(self, models_dir: str = "models"):
        self.data_loader = TrainingDataLoader()
        self.models_dir = models_dir
        self.training_results: dict = {}

        os.makedirs(models_dir, exist_ok=True)

    async def run_full_training(
        self,
        symbol: str = "XAU",
        days: int = 180,
        save_to_gcs: bool = True,
    ) -> dict:
        """Run complete training pipeline for all models.

        Args:
            symbol: Asset symbol to train on
            days: Days of historical data to use
            save_to_gcs: Upload trained models to GCS

        Returns:
            Training results for all models
        """
        logger.info("Starting full training pipeline", symbol=symbol, days=days)
        start_time = datetime.utcnow()

        results = {
            "symbol": symbol,
            "training_days": days,
            "started_at": start_time.isoformat(),
            "models": {},
        }

        # Load training data
        try:
            X, y = await self.data_loader.build_training_dataset(symbol, days)
            logger.info("Training data loaded", samples=len(X), features=X.shape[1])
        except ValueError as e:
            logger.error("Insufficient training data", error=str(e))
            results["error"] = str(e)
            results["status"] = "failed"
            return results

        # Walk-forward split: 80% train, 20% validation
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]

        logger.info("Data split", train=len(X_train), val=len(X_val))

        # Train each model
        results["models"]["random_forest"] = await self._train_random_forest(
            X_train, y_train, X_val, y_val
        )
        results["models"]["xgboost"] = await self._train_xgboost(
            X_train, y_train, X_val, y_val
        )
        results["models"]["arima"] = await self._train_arima(symbol, days)
        results["models"]["lstm"] = await self._train_lstm(symbol, days)

        # Upload to GCS if requested
        if save_to_gcs:
            gcs_paths = await self._upload_models_to_gcs(symbol)
            results["gcs_paths"] = gcs_paths

        end_time = datetime.utcnow()
        results["completed_at"] = end_time.isoformat()
        results["duration_seconds"] = (end_time - start_time).total_seconds()
        results["status"] = "completed"

        # Save training report
        report_path = os.path.join(self.models_dir, "training_report.json")
        with open(report_path, "w") as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(
            "Training pipeline complete",
            duration=results["duration_seconds"],
            models_trained=sum(
                1 for m in results["models"].values()
                if m.get("status") == "trained"
            ),
        )

        self.training_results = results
        return results

    async def _train_random_forest(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> dict:
        """Train Random Forest model."""
        try:
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.preprocessing import StandardScaler
            import joblib

            logger.info("Training Random Forest", samples=len(X_train))

            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_val_scaled = scaler.transform(X_val)

            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=8,
                random_state=42,
                n_jobs=-1,
            )
            model.fit(X_train_scaled, y_train)

            # Evaluate
            train_pred = model.predict(X_train_scaled)
            val_pred = model.predict(X_val_scaled)

            train_mae = float(np.mean(np.abs(y_train - train_pred)))
            val_mae = float(np.mean(np.abs(y_val - val_pred)))

            # Direction accuracy
            train_dir_acc = float(np.mean(
                np.sign(train_pred) == np.sign(y_train)
            ))
            val_dir_acc = float(np.mean(
                np.sign(val_pred) == np.sign(y_val)
            ))

            # Save model and scaler
            model_path = os.path.join(self.models_dir, "rf_model.joblib")
            scaler_path = os.path.join(self.models_dir, "rf_scaler.joblib")
            joblib.dump(model, model_path)
            joblib.dump(scaler, scaler_path)

            # Feature importances
            feature_names = [
                'rsi', 'macd', 'ema_short', 'ema_medium', 'sentiment_score',
                'dxy', 'treasury_10y', 'cpi', 'wti_oil', 'vix', 'sp500',
                'ema_spread', 'usd_interest', 'fear_equity_ratio', 'inflation_energy',
            ]
            importances = {
                name: float(imp)
                for name, imp in sorted(
                    zip(feature_names, model.feature_importances_),
                    key=lambda x: x[1],
                    reverse=True,
                )
            }

            result = {
                "status": "trained",
                "train_mae": train_mae,
                "val_mae": val_mae,
                "train_direction_accuracy": train_dir_acc,
                "val_direction_accuracy": val_dir_acc,
                "feature_importances": importances,
                "model_path": model_path,
                "scaler_path": scaler_path,
            }

            logger.info(
                "Random Forest trained",
                val_mae=val_mae,
                val_dir_acc=f"{val_dir_acc:.1%}",
            )
            return result

        except ImportError:
            logger.warning("scikit-learn not available, skipping Random Forest")
            return {"status": "skipped", "reason": "scikit-learn not installed"}
        except Exception as e:
            logger.error("Random Forest training failed", error=str(e))
            return {"status": "failed", "error": str(e)}

    async def _train_xgboost(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> dict:
        """Train XGBoost model."""
        try:
            from ..ml_models.xgboost_predictor import XGBoostPredictor, XGBOOST_AVAILABLE

            if not XGBOOST_AVAILABLE:
                return {"status": "skipped", "reason": "xgboost not installed"}

            logger.info("Training XGBoost", samples=len(X_train))

            predictor = XGBoostPredictor(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                model_path=os.path.join(self.models_dir, "xgboost_gold_predictor.json"),
            )

            train_results = await predictor.train(
                X_train, y_train, X_val, y_val,
                early_stopping_rounds=20,
            )

            # Calculate direction accuracy on validation
            from sklearn.preprocessing import StandardScaler
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_val_scaled = scaler.transform(X_val)

            val_preds = []
            for i in range(len(X_val)):
                pred = await predictor.predict(X_val_scaled[i], current_price=1.0)
                val_preds.append(pred)

            val_preds = np.array(val_preds)
            val_dir_acc = float(np.mean(np.sign(val_preds) == np.sign(y_val)))

            result = {
                "status": "trained",
                **train_results,
                "val_direction_accuracy": val_dir_acc,
                "feature_importances": predictor.get_feature_importance(),
                "model_path": predictor.model_path,
            }

            logger.info("XGBoost trained", val_dir_acc=f"{val_dir_acc:.1%}")
            return result

        except Exception as e:
            logger.error("XGBoost training failed", error=str(e))
            return {"status": "failed", "error": str(e)}

    async def _train_arima(self, symbol: str, days: int) -> dict:
        """Train ARIMA model."""
        try:
            from ..ml_models.arima_predictor import ARIMAPredictor, ARIMA_AVAILABLE

            if not ARIMA_AVAILABLE:
                return {"status": "skipped", "reason": "pmdarima not installed"}

            prices = await self.data_loader.load_price_history(symbol, days)
            if len(prices) < 50:
                return {"status": "skipped", "reason": f"insufficient data ({len(prices)} samples)"}

            logger.info("Training ARIMA", samples=len(prices))

            predictor = ARIMAPredictor()
            fit_results = await predictor.auto_fit(prices, test_size=14)

            result = {
                "status": "trained",
                **fit_results,
            }

            logger.info("ARIMA trained", order=fit_results.get("order"))
            return result

        except Exception as e:
            logger.error("ARIMA training failed", error=str(e))
            return {"status": "failed", "error": str(e)}

    async def _train_lstm(self, symbol: str, days: int) -> dict:
        """Train LSTM model."""
        try:
            from ..ml_models.lstm_predictor import LSTMPredictor, TF_AVAILABLE

            if not TF_AVAILABLE:
                return {"status": "skipped", "reason": "tensorflow not installed"}

            X, y = await self.data_loader.build_lstm_dataset(symbol, days, lookback=30)
            if len(X) < 50:
                return {"status": "skipped", "reason": f"insufficient sequences ({len(X)})"}

            logger.info("Training LSTM", sequences=len(X))

            predictor = LSTMPredictor(
                lookback_window=30,
                num_features=10,
                model_path=os.path.join(self.models_dir, "lstm_gold_predictor.keras"),
            )

            train_results = await predictor.train(
                training_data=np.concatenate([
                    X.reshape(-1, X.shape[-1]),
                ]),
                epochs=50,
                batch_size=32,
                validation_split=0.2,
            )

            result = {
                "status": "trained",
                **train_results,
                "model_path": predictor.model_path,
            }

            logger.info("LSTM trained", final_loss=train_results.get("final_loss"))
            return result

        except Exception as e:
            logger.error("LSTM training failed", error=str(e))
            return {"status": "failed", "error": str(e)}

    async def _upload_models_to_gcs(self, symbol: str) -> dict:
        """Upload trained models to Google Cloud Storage."""
        try:
            from google.cloud import storage

            bucket_name = f"{settings.google_cloud_project}-models"
            client = storage.Client(project=settings.google_cloud_project)

            try:
                bucket = client.get_bucket(bucket_name)
            except Exception:
                bucket = client.create_bucket(bucket_name, location="us-central1")
                logger.info("Created GCS bucket", bucket=bucket_name)

            date_prefix = datetime.utcnow().strftime("%Y%m%d")
            base_path = f"prediction-engine/{symbol}/{date_prefix}"

            uploaded = {}

            for filename in os.listdir(self.models_dir):
                filepath = os.path.join(self.models_dir, filename)
                if not os.path.isfile(filepath):
                    continue

                blob_path = f"{base_path}/{filename}"
                blob = bucket.blob(blob_path)
                blob.upload_from_filename(filepath)

                gcs_uri = f"gs://{bucket_name}/{blob_path}"
                uploaded[filename] = gcs_uri
                logger.info("Uploaded model to GCS", file=filename, uri=gcs_uri)

            # Also save as "latest" for easy loading
            for filename in os.listdir(self.models_dir):
                filepath = os.path.join(self.models_dir, filename)
                if not os.path.isfile(filepath):
                    continue

                blob_path = f"prediction-engine/{symbol}/latest/{filename}"
                blob = bucket.blob(blob_path)
                blob.upload_from_filename(filepath)

            logger.info("All models uploaded to GCS", count=len(uploaded))
            return uploaded

        except Exception as e:
            logger.error("GCS upload failed", error=str(e))
            return {"error": str(e)}

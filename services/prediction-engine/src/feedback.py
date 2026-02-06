"""Feedback loop for prediction outcome tracking and adaptive learning.

Records prediction outcomes, evaluates accuracy, and triggers
weight optimization when performance drops.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from sentilyze_core import get_logger, get_settings

from .learning import (
    PerformanceTracker,
    PredictionRecord,
    IndicatorScorer,
    RegimeDetector,
    WeightOptimizer,
    OptimizedWeights,
)

logger = get_logger(__name__)
settings = get_settings()


class FeedbackLoop:
    """Manages prediction outcome tracking and adaptive weight optimization."""

    def __init__(self):
        self.performance_tracker = PerformanceTracker()
        self.indicator_scorer = IndicatorScorer()
        self.regime_detector = RegimeDetector()
        self.weight_optimizer = WeightOptimizer(
            performance_tracker=self.performance_tracker,
            indicator_scorer=self.indicator_scorer,
            regime_detector=self.regime_detector,
            min_predictions_for_optimization=50,
            max_weight_change=0.1,
        )
        self._predictions_since_last_optimization = 0
        self._bigquery_client = None

    def _get_bq_client(self):
        if self._bigquery_client is None:
            try:
                from google.cloud import bigquery
                self._bigquery_client = bigquery.Client(
                    project=settings.google_cloud_project
                )
            except Exception as e:
                logger.warning("BigQuery client not available for feedback", error=str(e))
        return self._bigquery_client

    async def record_prediction(
        self,
        prediction_id: str,
        symbol: str,
        market_type: str,
        prediction_type: str,
        predicted_direction: str,
        predicted_price: float,
        current_price: float,
        confidence_score: int,
        technical_signal: float,
        sentiment_score: float,
        ml_prediction: float,
        indicator_signals: Optional[dict] = None,
        weights_used: Optional[dict] = None,
        market_regime: str = "unknown",
    ) -> None:
        """Record a new prediction for outcome tracking."""
        # Calculate expiration based on prediction type
        expiry_map = {
            "1h": timedelta(hours=1),
            "2h": timedelta(hours=2),
            "3h": timedelta(hours=3),
            "4h": timedelta(hours=4),
            "30m": timedelta(minutes=30),
            "6h": timedelta(hours=6),
        }
        expiry_delta = expiry_map.get(prediction_type, timedelta(hours=1))

        record = PredictionRecord(
            prediction_id=prediction_id,
            symbol=symbol,
            market_type=market_type,
            prediction_type=prediction_type,
            predicted_direction=predicted_direction,
            predicted_price=predicted_price,
            current_price=current_price,
            confidence_score=confidence_score,
            technical_signal=technical_signal,
            sentiment_score=sentiment_score,
            ml_prediction=ml_prediction,
            indicator_signals=indicator_signals or {},
            weights_used=weights_used or settings.prediction_weights,
            market_regime=market_regime,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + expiry_delta,
        )

        await self.performance_tracker.record_prediction(record)

        # Also save to BigQuery for persistence
        await self._save_prediction_to_bq(record)

        self._predictions_since_last_optimization += 1

        logger.debug(
            "Prediction recorded for feedback",
            prediction_id=prediction_id,
            symbol=symbol,
            direction=predicted_direction,
        )

    async def record_outcome(
        self,
        prediction_id: str,
        actual_price: float,
    ) -> Optional[dict]:
        """Record actual outcome for a prediction.

        Returns outcome dict if found, None otherwise.
        """
        outcome = await self.performance_tracker.record_outcome(
            prediction_id, actual_price
        )

        if outcome is None:
            return None

        # Record indicator signals for indicator scorer
        record = self._find_record(prediction_id)
        if record and record.indicator_signals:
            actual_direction = "UP" if actual_price > record.current_price * 1.0005 else (
                "DOWN" if actual_price < record.current_price * 0.9995 else "FLAT"
            )

            for indicator_name, signal_value in record.indicator_signals.items():
                self.indicator_scorer.record_signal(
                    indicator_name=indicator_name,
                    signal_value=signal_value,
                    actual_direction=actual_direction,
                    market_regime=record.market_regime,
                )

        # Save outcome to BigQuery
        await self._save_outcome_to_bq(prediction_id, actual_price, outcome)

        return outcome

    async def check_and_resolve_expired(self) -> int:
        """Check for expired predictions and fetch actual prices.

        Returns number of outcomes resolved.
        """
        pending = self.performance_tracker.get_pending_predictions()
        now = datetime.utcnow()
        resolved = 0

        for record in pending:
            if record.expires_at and now > record.expires_at:
                actual_price = await self._fetch_actual_price(
                    record.symbol, record.expires_at
                )
                if actual_price:
                    await self.record_outcome(record.prediction_id, actual_price)
                    resolved += 1

        if resolved > 0:
            logger.info("Resolved expired predictions", count=resolved)

        return resolved

    async def maybe_optimize_weights(
        self,
        prices: list[float],
        symbol: Optional[str] = None,
        prediction_type: Optional[str] = None,
    ) -> Optional[OptimizedWeights]:
        """Check if weight optimization is needed and run if so."""
        should = self.weight_optimizer.should_reoptimize(
            predictions_since_last=self._predictions_since_last_optimization,
        )

        if not should:
            return None

        logger.info("Running weight optimization")

        optimized = self.weight_optimizer.optimize(
            prices=prices,
            symbol=symbol,
            prediction_type=prediction_type,
        )

        self._predictions_since_last_optimization = 0

        logger.info(
            "Weights optimized",
            component_weights=optimized.component_weights,
            regime=optimized.market_regime,
            confidence=f"{optimized.optimization_confidence:.0%}",
        )

        return optimized

    def get_current_weights(self) -> dict:
        """Get current optimized weights or defaults."""
        current = self.weight_optimizer.get_current_weights()
        if current:
            return current.component_weights
        return settings.prediction_weights.copy()

    def get_accuracy_report(self) -> dict:
        """Get comprehensive accuracy report."""
        metrics = self.performance_tracker.get_accuracy_metrics()

        indicator_scores = {}
        all_scores = self.indicator_scorer.get_all_scores()
        for name, score in all_scores.items():
            indicator_scores[name] = {
                "accuracy": score.accuracy,
                "total_signals": score.total_signals,
                "weight_multiplier": score.weight_multiplier,
                "recent_accuracy": score.recent_accuracy,
            }

        optimization = self.weight_optimizer.get_summary()

        return {
            "overall": {
                "total_predictions": metrics.total_predictions,
                "direction_accuracy": metrics.direction_accuracy,
                "avg_price_error": metrics.avg_price_error,
                "avg_confidence_when_correct": metrics.avg_confidence_when_correct,
                "avg_confidence_when_wrong": metrics.avg_confidence_when_wrong,
            },
            "indicators": indicator_scores,
            "optimization": optimization,
        }

    def _find_record(self, prediction_id: str) -> Optional[PredictionRecord]:
        """Find a prediction record by ID."""
        for record in self.performance_tracker._records:
            if record.prediction_id == prediction_id:
                return record
        return None

    async def _fetch_actual_price(
        self, symbol: str, at_time: datetime
    ) -> Optional[float]:
        """Fetch actual price at a given time from BigQuery."""
        client = self._get_bq_client()
        if not client:
            return None

        try:
            query = """
            SELECT
                CAST(JSON_EXTRACT_SCALAR(payload, '$.price') AS FLOAT64) as price
            FROM `{project}.{dataset}.raw_events`
            WHERE symbol LIKE @symbol_pattern
              AND timestamp BETWEEN
                  TIMESTAMP_SUB(@target_time, INTERVAL 30 MINUTE)
                  AND TIMESTAMP_ADD(@target_time, INTERVAL 30 MINUTE)
              AND JSON_EXTRACT_SCALAR(payload, '$.price') IS NOT NULL
            ORDER BY ABS(TIMESTAMP_DIFF(timestamp, @target_time, SECOND))
            LIMIT 1
            """.format(
                project=settings.google_cloud_project,
                dataset=settings.bigquery_dataset,
            )

            from google.cloud import bigquery
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("symbol_pattern", "STRING", f"%{symbol}%"),
                    bigquery.ScalarQueryParameter("target_time", "TIMESTAMP", at_time),
                ]
            )

            results = client.query(query, job_config=job_config).result()
            for row in results:
                if row.price:
                    return float(row.price)

        except Exception as e:
            logger.error("Failed to fetch actual price", error=str(e))

        return None

    async def _save_prediction_to_bq(self, record: PredictionRecord) -> None:
        """Save prediction record to BigQuery for persistence."""
        client = self._get_bq_client()
        if not client:
            return

        try:
            table_ref = f"{settings.google_cloud_project}.{settings.bigquery_dataset}.prediction_feedback"

            rows = [{
                "prediction_id": record.prediction_id,
                "symbol": record.symbol,
                "market_type": record.market_type,
                "prediction_type": record.prediction_type,
                "predicted_direction": record.predicted_direction,
                "predicted_price": record.predicted_price,
                "current_price": record.current_price,
                "confidence_score": record.confidence_score,
                "technical_signal": record.technical_signal,
                "sentiment_score": record.sentiment_score,
                "ml_prediction": record.ml_prediction,
                "market_regime": record.market_regime,
                "weights_used": json.dumps(record.weights_used),
                "created_at": record.created_at.isoformat(),
                "expires_at": record.expires_at.isoformat() if record.expires_at else None,
            }]

            errors = client.insert_rows_json(table_ref, rows)
            if errors:
                logger.warning("BQ insert errors for prediction", errors=errors)

        except Exception as e:
            logger.debug("Could not save prediction to BQ (non-fatal)", error=str(e))

    async def _save_outcome_to_bq(
        self, prediction_id: str, actual_price: float, outcome: dict
    ) -> None:
        """Save outcome to BigQuery."""
        client = self._get_bq_client()
        if not client:
            return

        try:
            table_ref = f"{settings.google_cloud_project}.{settings.bigquery_dataset}.prediction_outcomes"

            rows = [{
                "prediction_id": prediction_id,
                "actual_price": actual_price,
                "actual_direction": outcome.get("actual_direction", "FLAT"),
                "direction_correct": outcome.get("direction_correct", False),
                "price_error_percent": outcome.get("price_error_percent", 0),
                "recorded_at": datetime.utcnow().isoformat(),
            }]

            errors = client.insert_rows_json(table_ref, rows)
            if errors:
                logger.warning("BQ insert errors for outcome", errors=errors)

        except Exception as e:
            logger.debug("Could not save outcome to BQ (non-fatal)", error=str(e))


# Need json import for weights serialization
import json

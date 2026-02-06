"""Feedback loop for prediction outcome tracking and adaptive learning.

Records prediction outcomes, evaluates accuracy, triggers
weight optimization when performance drops, and generates
daily analysis reports with failure reasoning.
"""

import json
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

    async def generate_daily_report(self, date: Optional[datetime] = None) -> dict:
        """Generate comprehensive daily prediction report with failure analysis.

        Analyzes all predictions from the given day, identifies why predictions
        succeeded or failed, and produces actionable lessons for improvement.

        Args:
            date: Date to report on (defaults to today)

        Returns:
            Daily report dictionary
        """
        if date is None:
            date = datetime.utcnow()

        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        # Gather completed predictions for the day
        all_records = self.performance_tracker._records
        day_records = [
            r for r in all_records
            if r.created_at >= day_start
            and r.created_at < day_end
            and r.direction_correct is not None
        ]

        if not day_records:
            return {
                "date": day_start.strftime("%Y-%m-%d"),
                "status": "no_data",
                "message": "No completed predictions for this day",
            }

        correct = [r for r in day_records if r.direction_correct]
        wrong = [r for r in day_records if not r.direction_correct]
        total = len(day_records)
        accuracy = len(correct) / total if total else 0

        # Analyze each prediction
        prediction_details = []
        for record in day_records:
            analysis = self._analyze_prediction(record)
            prediction_details.append(analysis)

        # Aggregate failure reasons
        failure_reasons = {}
        for detail in prediction_details:
            if not detail["direction_correct"]:
                for reason in detail["failure_reasons"]:
                    failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

        # Sort failure reasons by frequency
        sorted_failures = sorted(
            failure_reasons.items(), key=lambda x: x[1], reverse=True
        )

        # Component accuracy breakdown
        component_stats = self._component_accuracy_for_day(day_records)

        # Indicator accuracy breakdown
        indicator_stats = self._indicator_accuracy_for_day(day_records)

        # Regime breakdown
        regime_stats = self._regime_breakdown_for_day(day_records)

        # Confidence calibration
        calibration = self._confidence_calibration(day_records)

        # Lessons learned - actionable insights
        lessons = self._derive_lessons(
            day_records, sorted_failures, component_stats, indicator_stats
        )

        report = {
            "date": day_start.strftime("%Y-%m-%d"),
            "summary": {
                "total_predictions": total,
                "correct": len(correct),
                "wrong": len(wrong),
                "accuracy": round(accuracy, 4),
                "accuracy_pct": f"{accuracy:.1%}",
                "avg_price_error_pct": round(
                    sum(r.price_error_percent or 0 for r in day_records) / total, 4
                ),
            },
            "component_accuracy": component_stats,
            "indicator_accuracy": indicator_stats,
            "regime_breakdown": regime_stats,
            "confidence_calibration": calibration,
            "top_failure_reasons": [
                {"reason": reason, "count": count}
                for reason, count in sorted_failures[:10]
            ],
            "lessons_learned": lessons,
            "predictions": prediction_details,
        }

        # Save report to BigQuery
        await self._save_daily_report_to_bq(report)

        logger.info(
            "Daily report generated",
            date=day_start.strftime("%Y-%m-%d"),
            accuracy=f"{accuracy:.1%}",
            total=total,
            lessons=len(lessons),
        )

        return report

    def _analyze_prediction(self, record: PredictionRecord) -> dict:
        """Analyze a single prediction - determine why it succeeded or failed.

        Returns detailed analysis with reasoning.
        """
        analysis = {
            "prediction_id": record.prediction_id,
            "symbol": record.symbol,
            "prediction_type": record.prediction_type,
            "predicted_direction": record.predicted_direction,
            "actual_direction": record.actual_direction,
            "direction_correct": record.direction_correct,
            "predicted_price": record.predicted_price,
            "actual_price": record.actual_price,
            "current_price": record.current_price,
            "price_error_pct": round(record.price_error_percent or 0, 4),
            "confidence_score": record.confidence_score,
            "market_regime": record.market_regime,
            "created_at": record.created_at.isoformat(),
            "success_factors": [],
            "failure_reasons": [],
        }

        # Component signal analysis
        tech_direction = self._signal_to_direction(record.technical_signal)
        sent_direction = self._signal_to_direction(record.sentiment_score)
        ml_direction = self._signal_to_direction(record.ml_prediction)

        tech_correct = tech_direction == record.actual_direction
        sent_correct = sent_direction == record.actual_direction
        ml_correct = ml_direction == record.actual_direction

        analysis["component_signals"] = {
            "technical": {
                "signal": round(record.technical_signal, 4),
                "direction": tech_direction,
                "correct": tech_correct,
            },
            "sentiment": {
                "signal": round(record.sentiment_score, 4),
                "direction": sent_direction,
                "correct": sent_correct,
            },
            "ml": {
                "signal": round(record.ml_prediction, 4),
                "direction": ml_direction,
                "correct": ml_correct,
            },
        }

        # Indicator signal analysis
        indicator_analysis = {}
        for ind_name, ind_signal in record.indicator_signals.items():
            ind_direction = self._signal_to_direction(ind_signal)
            ind_correct = ind_direction == record.actual_direction
            indicator_analysis[ind_name] = {
                "signal": round(ind_signal, 4),
                "direction": ind_direction,
                "correct": ind_correct,
            }
        analysis["indicator_signals"] = indicator_analysis

        if record.direction_correct:
            # Why it succeeded
            if tech_correct and sent_correct and ml_correct:
                analysis["success_factors"].append("all_components_agreed_correctly")
            if tech_correct:
                analysis["success_factors"].append("technical_analysis_correct")
            if sent_correct:
                analysis["success_factors"].append("sentiment_analysis_correct")
            if ml_correct:
                analysis["success_factors"].append("ml_model_correct")
            if record.confidence_score >= 70:
                analysis["success_factors"].append("high_confidence_justified")

            # Check which indicators contributed
            correct_indicators = [
                name for name, info in indicator_analysis.items() if info["correct"]
            ]
            if correct_indicators:
                analysis["success_factors"].append(
                    f"correct_indicators: {', '.join(correct_indicators)}"
                )
        else:
            # Why it failed - detailed failure analysis
            components_wrong = []
            if not tech_correct:
                components_wrong.append("technical")
            if not sent_correct:
                components_wrong.append("sentiment")
            if not ml_correct:
                components_wrong.append("ml")

            if len(components_wrong) == 3:
                analysis["failure_reasons"].append("all_components_wrong")
            else:
                for comp in components_wrong:
                    analysis["failure_reasons"].append(f"{comp}_signal_misleading")

            # Component conflict
            directions = {tech_direction, sent_direction, ml_direction}
            directions.discard("FLAT")
            if len(directions) > 1:
                analysis["failure_reasons"].append("component_signals_conflicted")

            # Confidence too high for wrong prediction
            if record.confidence_score >= 70:
                analysis["failure_reasons"].append("overconfident_wrong_prediction")
            elif record.confidence_score >= 50:
                analysis["failure_reasons"].append("moderate_confidence_wrong")

            # Regime mismatch
            if record.market_regime == "volatile":
                analysis["failure_reasons"].append("volatile_regime_unpredictable")
            elif record.market_regime == "sideways":
                analysis["failure_reasons"].append("sideways_regime_false_signal")

            # Check individual indicators
            wrong_indicators = [
                name for name, info in indicator_analysis.items() if not info["correct"]
            ]
            if wrong_indicators:
                analysis["failure_reasons"].append(
                    f"wrong_indicators: {', '.join(wrong_indicators)}"
                )

            # Price error magnitude
            if (record.price_error_percent or 0) > 1.0:
                analysis["failure_reasons"].append("large_price_error_gt_1pct")
            elif (record.price_error_percent or 0) > 0.5:
                analysis["failure_reasons"].append("moderate_price_error_gt_05pct")

        return analysis

    def _signal_to_direction(self, signal: float) -> str:
        """Convert a signal value to direction string."""
        if signal > 0.1:
            return "UP"
        elif signal < -0.1:
            return "DOWN"
        return "FLAT"

    def _component_accuracy_for_day(
        self, records: list[PredictionRecord]
    ) -> dict:
        """Calculate per-component accuracy for the day."""
        stats = {}
        for component, attr in [
            ("technical", "technical_signal"),
            ("sentiment", "sentiment_score"),
            ("ml", "ml_prediction"),
        ]:
            correct = 0
            total = 0
            for r in records:
                if r.actual_direction is None:
                    continue
                signal = getattr(r, attr, 0)
                sig_dir = self._signal_to_direction(signal)
                if sig_dir == r.actual_direction:
                    correct += 1
                total += 1
            acc = correct / total if total > 0 else 0
            stats[component] = {
                "correct": correct,
                "total": total,
                "accuracy": round(acc, 4),
                "accuracy_pct": f"{acc:.1%}",
            }
        return stats

    def _indicator_accuracy_for_day(
        self, records: list[PredictionRecord]
    ) -> dict:
        """Calculate per-indicator accuracy for the day."""
        indicator_results: dict[str, dict] = {}
        for r in records:
            if r.actual_direction is None:
                continue
            for ind_name, ind_signal in r.indicator_signals.items():
                if ind_name not in indicator_results:
                    indicator_results[ind_name] = {"correct": 0, "total": 0}
                ind_dir = self._signal_to_direction(ind_signal)
                if ind_dir == r.actual_direction:
                    indicator_results[ind_name]["correct"] += 1
                indicator_results[ind_name]["total"] += 1

        stats = {}
        for name, data in indicator_results.items():
            acc = data["correct"] / data["total"] if data["total"] > 0 else 0
            stats[name] = {
                "correct": data["correct"],
                "total": data["total"],
                "accuracy": round(acc, 4),
                "accuracy_pct": f"{acc:.1%}",
            }
        return stats

    def _regime_breakdown_for_day(
        self, records: list[PredictionRecord]
    ) -> dict:
        """Break down accuracy by market regime for the day."""
        regime_data: dict[str, dict] = {}
        for r in records:
            regime = r.market_regime
            if regime not in regime_data:
                regime_data[regime] = {"correct": 0, "total": 0}
            regime_data[regime]["total"] += 1
            if r.direction_correct:
                regime_data[regime]["correct"] += 1

        stats = {}
        for regime, data in regime_data.items():
            acc = data["correct"] / data["total"] if data["total"] > 0 else 0
            stats[regime] = {
                "correct": data["correct"],
                "total": data["total"],
                "accuracy": round(acc, 4),
                "accuracy_pct": f"{acc:.1%}",
            }
        return stats

    def _confidence_calibration(self, records: list[PredictionRecord]) -> dict:
        """Check if confidence scores are well-calibrated.

        High confidence should correlate with correct predictions.
        """
        buckets = {
            "low_0_40": {"correct": 0, "total": 0},
            "medium_40_60": {"correct": 0, "total": 0},
            "high_60_80": {"correct": 0, "total": 0},
            "very_high_80_100": {"correct": 0, "total": 0},
        }

        for r in records:
            if r.confidence_score < 40:
                bucket = "low_0_40"
            elif r.confidence_score < 60:
                bucket = "medium_40_60"
            elif r.confidence_score < 80:
                bucket = "high_60_80"
            else:
                bucket = "very_high_80_100"

            buckets[bucket]["total"] += 1
            if r.direction_correct:
                buckets[bucket]["correct"] += 1

        result = {}
        well_calibrated = True
        for name, data in buckets.items():
            if data["total"] == 0:
                result[name] = {"accuracy": 0, "total": 0, "status": "no_data"}
                continue
            acc = data["correct"] / data["total"]
            result[name] = {
                "accuracy": round(acc, 4),
                "accuracy_pct": f"{acc:.1%}",
                "total": data["total"],
            }
            # High confidence should be more accurate than low
            if name.startswith("very_high") and acc < 0.5:
                result[name]["status"] = "overconfident"
                well_calibrated = False
            elif name.startswith("low") and acc > 0.7:
                result[name]["status"] = "underconfident"
                well_calibrated = False
            else:
                result[name]["status"] = "ok"

        result["well_calibrated"] = well_calibrated
        return result

    def _derive_lessons(
        self,
        records: list[PredictionRecord],
        failure_reasons: list[tuple[str, int]],
        component_stats: dict,
        indicator_stats: dict,
    ) -> list[dict]:
        """Derive actionable lessons from the day's performance.

        These lessons directly feed into weight optimization.
        """
        lessons = []
        total = len(records)

        # Lesson 1: Component reliability
        for comp, stats in component_stats.items():
            acc = stats["accuracy"]
            if acc < 0.4:
                lessons.append({
                    "type": "reduce_weight",
                    "target": comp,
                    "reason": f"{comp} accuracy only {stats['accuracy_pct']} today - signals are misleading",
                    "action": f"Reduce {comp} weight in next optimization cycle",
                    "severity": "high",
                })
            elif acc > 0.65:
                lessons.append({
                    "type": "increase_weight",
                    "target": comp,
                    "reason": f"{comp} performed well at {stats['accuracy_pct']} - signals are reliable",
                    "action": f"Increase {comp} weight in next optimization cycle",
                    "severity": "low",
                })

        # Lesson 2: Indicator reliability
        for ind, stats in indicator_stats.items():
            if stats["total"] < 3:
                continue
            acc = stats["accuracy"]
            if acc < 0.35:
                lessons.append({
                    "type": "reduce_indicator_weight",
                    "target": ind,
                    "reason": f"{ind} indicator only {stats['accuracy_pct']} accurate - consistently wrong",
                    "action": f"Reduce {ind} weight or consider disabling in current regime",
                    "severity": "high",
                })
            elif acc > 0.7:
                lessons.append({
                    "type": "increase_indicator_weight",
                    "target": ind,
                    "reason": f"{ind} indicator excellent at {stats['accuracy_pct']} - strong signal",
                    "action": f"Increase {ind} weight",
                    "severity": "low",
                })

        # Lesson 3: Overconfidence
        for reason, count in failure_reasons:
            if reason == "overconfident_wrong_prediction" and count >= 2:
                lessons.append({
                    "type": "calibration",
                    "target": "confidence_scoring",
                    "reason": f"System was overconfident {count} times today - high confidence predictions were wrong",
                    "action": "Apply confidence dampening factor, reduce confidence scores by 10-15%",
                    "severity": "high",
                })
                break

        # Lesson 4: Regime-specific issues
        for reason, count in failure_reasons:
            if "volatile_regime" in reason and count >= 2:
                lessons.append({
                    "type": "regime_adjustment",
                    "target": "volatile_regime",
                    "reason": f"Volatile market caused {count} wrong predictions - signals unreliable in volatility",
                    "action": "Increase ML weight and decrease technical weight during volatile regimes",
                    "severity": "medium",
                })
                break
            if "sideways_regime" in reason and count >= 2:
                lessons.append({
                    "type": "regime_adjustment",
                    "target": "sideways_regime",
                    "reason": f"Sideways market generated {count} false signals",
                    "action": "Widen FLAT threshold in sideways regime, reduce position confidence",
                    "severity": "medium",
                })
                break

        # Lesson 5: Component conflict
        for reason, count in failure_reasons:
            if reason == "component_signals_conflicted" and count >= 3:
                lessons.append({
                    "type": "conflict_handling",
                    "target": "ensemble",
                    "reason": f"Components conflicted {count} times and the wrong side won",
                    "action": "When components disagree, reduce confidence score and favor the historically more accurate component",
                    "severity": "medium",
                })
                break

        return lessons

    async def _save_daily_report_to_bq(self, report: dict) -> None:
        """Save daily report to BigQuery."""
        client = self._get_bq_client()
        if not client:
            return

        try:
            table_ref = f"{settings.google_cloud_project}.{settings.bigquery_dataset}.daily_prediction_reports"

            rows = [{
                "report_date": report["date"],
                "total_predictions": report["summary"]["total_predictions"],
                "correct_predictions": report["summary"]["correct"],
                "accuracy": report["summary"]["accuracy"],
                "avg_price_error_pct": report["summary"]["avg_price_error_pct"],
                "component_accuracy": json.dumps(report["component_accuracy"]),
                "indicator_accuracy": json.dumps(report["indicator_accuracy"]),
                "regime_breakdown": json.dumps(report["regime_breakdown"]),
                "top_failure_reasons": json.dumps(report["top_failure_reasons"]),
                "lessons_learned": json.dumps(report["lessons_learned"]),
                "confidence_calibration": json.dumps(report["confidence_calibration"]),
                "created_at": datetime.utcnow().isoformat(),
            }]

            errors = client.insert_rows_json(table_ref, rows)
            if errors:
                logger.warning("BQ insert errors for daily report", errors=errors)

        except Exception as e:
            logger.debug("Could not save daily report to BQ (non-fatal)", error=str(e))

    async def apply_lessons(self, lessons: list[dict]) -> dict:
        """Apply lessons from daily report to improve future predictions.

        Feeds lessons back into WeightOptimizer and IndicatorScorer.

        Returns summary of applied adjustments.
        """
        applied = []

        for lesson in lessons:
            lesson_type = lesson.get("type", "")
            target = lesson.get("target", "")
            severity = lesson.get("severity", "low")

            # Only auto-apply high severity lessons
            if severity != "high":
                continue

            if lesson_type == "reduce_weight" and target in ("technical", "sentiment", "ml"):
                current = self.weight_optimizer.get_current_weights()
                if current:
                    old_val = current.component_weights.get(target, 0.33)
                    # Reduce by 5%
                    adjustment = -0.05
                    current.component_weights[target] = max(0.1, old_val + adjustment)
                    # Renormalize
                    total = sum(current.component_weights.values())
                    current.component_weights = {
                        k: v / total for k, v in current.component_weights.items()
                    }
                    applied.append({
                        "action": f"Reduced {target} weight from {old_val:.2f} to {current.component_weights[target]:.2f}",
                        "lesson": lesson["reason"],
                    })

            elif lesson_type == "reduce_indicator_weight":
                # Reduce indicator's score multiplier
                score = self.indicator_scorer.get_score(target)
                if score:
                    old_mult = score.weight_multiplier
                    score.weight_multiplier = max(0.2, old_mult * 0.8)
                    applied.append({
                        "action": f"Reduced {target} indicator multiplier from {old_mult:.2f} to {score.weight_multiplier:.2f}",
                        "lesson": lesson["reason"],
                    })

            elif lesson_type == "calibration":
                applied.append({
                    "action": "Flagged for confidence dampening in next prediction cycle",
                    "lesson": lesson["reason"],
                })

        logger.info("Applied lessons from daily report", count=len(applied))
        return {"applied_count": len(applied), "adjustments": applied}

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

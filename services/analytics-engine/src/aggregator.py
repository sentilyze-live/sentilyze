"""Data aggregation and metrics computation."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sentilyze_core import BigQueryClient, get_logger

from .config import get_analytics_settings

logger = get_logger(__name__)
settings = get_analytics_settings()


@dataclass(frozen=True)
class MaterializationWindow:
    """Time window for materialization."""
    window_start: datetime
    window_end: datetime


def _utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


def _to_iso_z(dt: datetime) -> str:
    """Convert datetime to ISO format with Z suffix."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class AnalyticsAggregator:
    """Aggregates data and computes analytics metrics."""

    def __init__(self, bigquery_client: BigQueryClient):
        self.bigquery = bigquery_client

    async def compute_metrics(
        self,
        window: MaterializationWindow,
    ) -> dict[str, Optional[float]]:
        """Compute analytics metrics for a time window."""
        try:
            # Import here to avoid dependency issues
            from google.cloud import bigquery as bq

            params = [
                bq.ScalarQueryParameter("window_start", "TIMESTAMP", window.window_start),
                bq.ScalarQueryParameter("window_end", "TIMESTAMP", window.window_end),
            ]

            # Query total events and average sentiment
            q_counts = f"""
            SELECT
              COUNT(*) AS total_events,
              AVG(sentiment.score) AS avg_sentiment
            FROM `{self.bigquery.project_id}.{self.bigquery.dataset}.{self.bigquery.SENTIMENT_ANALYSIS_TABLE}`
            WHERE processed_at >= @window_start AND processed_at < @window_end
            """.strip()

            rows = list(await self.bigquery.execute_query(q_counts, parameters=params))
            r0: dict[str, Any] = dict(rows[0]) if rows else {}

            total_events = float(r0.get("total_events") or 0.0)
            avg_sentiment_raw = r0.get("avg_sentiment")
            avg_sentiment = float(avg_sentiment_raw) if avg_sentiment_raw is not None else None

            # Query distinct symbols
            q_symbols = f"""
            SELECT
              COUNT(DISTINCT sym) AS distinct_symbols
            FROM `{self.bigquery.project_id}.{self.bigquery.dataset}.{self.bigquery.SENTIMENT_ANALYSIS_TABLE}`,
            UNNEST(symbols) AS sym
            WHERE processed_at >= @window_start AND processed_at < @window_end
            """.strip()

            sym_rows = list(await self.bigquery.execute_query(q_symbols, parameters=params))
            s0: dict[str, Any] = dict(sym_rows[0]) if sym_rows else {}
            distinct_symbols = float(s0.get("distinct_symbols") or 0.0)

            return {
                "processed_events_total": total_events,
                "processed_events_avg_sentiment": avg_sentiment,
                "processed_events_distinct_symbols": distinct_symbols,
            }

        except Exception as e:
            logger.error("Failed to compute metrics", error=str(e))
            return {
                "processed_events_total": 0.0,
                "processed_events_avg_sentiment": None,
                "processed_events_distinct_symbols": 0.0,
            }

    async def write_metrics(
        self,
        window: MaterializationWindow,
        metrics: dict[str, Optional[float]],
        created_at: Optional[datetime] = None,
    ) -> int:
        """Write computed metrics to BigQuery."""
        created_at = created_at or _utc_now()

        rows: list[dict[str, Any]] = []
        row_ids: list[str] = []
        window_id = f"{_to_iso_z(window.window_start)}:{_to_iso_z(window.window_end)}"

        for metric, value in metrics.items():
            rows.append(
                {
                    "metric": metric,
                    "value": value,
                    "window_start": _to_iso_z(window.window_start),
                    "window_end": _to_iso_z(window.window_end),
                    "created_at": _to_iso_z(created_at),
                }
            )
            row_ids.append(f"{metric}:{window_id}")

        try:
            errors = await self.bigquery.insert_rows(
                self.bigquery.dataset,
                self.bigquery.ANALYTICS_SUMMARY_TABLE,
                rows,
                row_ids=row_ids,
            )
            if errors:
                logger.error(
                    "Analytics materialization insert errors",
                    error_count=len(errors),
                    first_error=errors[0] if errors else None,
                )
                raise RuntimeError(f"Failed to insert analytics metrics: {errors[:1]}")

            logger.info(
                "Analytics metrics materialized",
                window_start=_to_iso_z(window.window_start),
                window_end=_to_iso_z(window.window_end),
                metrics_written=len(rows),
            )
            return len(rows)
        except Exception as e:
            logger.error("Failed to write metrics", error=str(e))
            raise

    async def get_sentiment_trend(
        self,
        symbol: str,
        days: int = 7,
    ) -> list[dict]:
        """Get sentiment trend for a symbol."""
        try:
            end = _utc_now()
            start = end - timedelta(days=days)

            query = f"""
            SELECT
              DATE(processed_at) as date,
              AVG(sentiment.score) as avg_sentiment,
              COUNT(*) as event_count,
              ARRAY_AGG(DISTINCT source) as sources
            FROM `{self.bigquery.project_id}.{self.bigquery.dataset}.{self.bigquery.SENTIMENT_ANALYSIS_TABLE}`
            WHERE processed_at >= TIMESTAMP(@start)
              AND processed_at < TIMESTAMP(@end)
              AND @symbol IN UNNEST(symbols)
            GROUP BY DATE(processed_at)
            ORDER BY date
            """

            from google.cloud import bigquery as bq
            params = [
                bq.ScalarQueryParameter("start", "TIMESTAMP", start),
                bq.ScalarQueryParameter("end", "TIMESTAMP", end),
                bq.ScalarQueryParameter("symbol", "STRING", symbol),
            ]

            rows = await self.bigquery.execute_query(query, parameters=params)
            return [dict(row) for row in rows]

        except Exception as e:
            logger.error("Failed to get sentiment trend", symbol=symbol, error=str(e))
            return []

    async def get_market_comparison(
        self,
        symbols: list[str],
        days: int = 7,
    ) -> dict:
        """Compare sentiment across multiple symbols."""
        try:
            end = _utc_now()
            start = end - timedelta(days=days)

            query = f"""
            SELECT
              sym as symbol,
              AVG(sentiment.score) as avg_sentiment,
              COUNT(*) as event_count,
              STDDEV(sentiment.score) as sentiment_std
            FROM `{self.bigquery.project_id}.{self.bigquery.dataset}.{self.bigquery.SENTIMENT_ANALYSIS_TABLE}`,
            UNNEST(symbols) AS sym
            WHERE processed_at >= TIMESTAMP(@start)
              AND processed_at < TIMESTAMP(@end)
              AND sym IN UNNEST(@symbols)
            GROUP BY sym
            ORDER BY avg_sentiment DESC
            """

            from google.cloud import bigquery as bq
            params = [
                bq.ScalarQueryParameter("start", "TIMESTAMP", start),
                bq.ScalarQueryParameter("end", "TIMESTAMP", end),
                bq.ScalarQueryParameter("symbols", "ARRAY<STRING>", symbols),
            ]

            rows = await self.bigquery.execute_query(query, parameters=params)
            return {
                "symbols": [dict(row) for row in rows],
                "days": days,
                "generated_at": _to_iso_z(_utc_now()),
            }

        except Exception as e:
            logger.error("Failed to get market comparison", error=str(e))
            return {"symbols": [], "days": days, "error": str(e)}

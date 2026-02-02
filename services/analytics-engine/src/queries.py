"""BigQuery queries for analytics."""

from datetime import datetime, timedelta
from typing import Any

from sentilyze_core import BigQueryClient, get_logger

from .config import get_analytics_settings

logger = get_logger(__name__)
settings = get_analytics_settings()


class AnalyticsQueries:
    """Predefined queries for analytics."""

    def __init__(self, bigquery_client: BigQueryClient):
        self.bigquery = bigquery_client

    def get_sentiment_by_symbol_query(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
    ) -> tuple[str, list]:
        """Get query for sentiment data by symbol."""
        query = f"""
        SELECT
          processed_at,
          sentiment.score as sentiment_score,
          sentiment.label as sentiment_label,
          source,
          content_preview as content_length
        FROM `{self.bigquery.project_id}.{self.bigquery.dataset}.{self.bigquery.SENTIMENT_ANALYSIS_TABLE}`
        WHERE processed_at >= TIMESTAMP(@start)
          AND processed_at < TIMESTAMP(@end)
          AND @symbol IN UNNEST(symbols)
        ORDER BY processed_at
        """

        from google.cloud import bigquery as bq
        params = [
            bq.ScalarQueryParameter("start", "TIMESTAMP", start),
            bq.ScalarQueryParameter("end", "TIMESTAMP", end),
            bq.ScalarQueryParameter("symbol", "STRING", symbol),
        ]

        return query, params

    def get_source_distribution_query(
        self,
        days: int = 7,
    ) -> tuple[str, list]:
        """Get query for source distribution."""
        end = datetime.utcnow()
        start = end - timedelta(days=days)

        query = f"""
        SELECT
          source,
          COUNT(*) as event_count,
          AVG(sentiment.score) as avg_sentiment
        FROM `{self.bigquery.project_id}.{self.bigquery.dataset}.{self.bigquery.SENTIMENT_ANALYSIS_TABLE}`
        WHERE processed_at >= TIMESTAMP(@start)
          AND processed_at < TIMESTAMP(@end)
        GROUP BY source
        ORDER BY event_count DESC
        """

        from google.cloud import bigquery as bq
        params = [
            bq.ScalarQueryParameter("start", "TIMESTAMP", start),
            bq.ScalarQueryParameter("end", "TIMESTAMP", end),
        ]

        return query, params

    def get_hourly_sentiment_query(
        self,
        symbol: str,
        hours: int = 24,
    ) -> tuple[str, list]:
        """Get query for hourly sentiment aggregation."""
        end = datetime.utcnow()
        start = end - timedelta(hours=hours)

        query = f"""
        SELECT
          TIMESTAMP_TRUNC(processed_at, HOUR) as hour,
          AVG(sentiment.score) as avg_sentiment,
          COUNT(*) as event_count
        FROM `{self.bigquery.project_id}.{self.bigquery.dataset}.{self.bigquery.SENTIMENT_ANALYSIS_TABLE}`
        WHERE processed_at >= TIMESTAMP(@start)
          AND processed_at < TIMESTAMP(@end)
          AND @symbol IN UNNEST(symbols)
        GROUP BY hour
        ORDER BY hour
        """

        from google.cloud import bigquery as bq
        params = [
            bq.ScalarQueryParameter("start", "TIMESTAMP", start),
            bq.ScalarQueryParameter("end", "TIMESTAMP", end),
            bq.ScalarQueryParameter("symbol", "STRING", symbol),
        ]

        return query, params

    def get_top_keywords_query(
        self,
        symbol: str,
        days: int = 7,
        limit: int = 20,
    ) -> tuple[str, list]:
        """Get query for top keywords by symbol."""
        end = datetime.utcnow()
        start = end - timedelta(days=days)

        query = f"""
        SELECT
          kw as keyword,
          COUNT(*) as mention_count,
          AVG(sentiment.score) as avg_sentiment
        FROM `{self.bigquery.project_id}.{self.bigquery.dataset}.{self.bigquery.SENTIMENT_ANALYSIS_TABLE}`,
        UNNEST(keywords) AS kw
        WHERE processed_at >= TIMESTAMP(@start)
          AND processed_at < TIMESTAMP(@end)
          AND @symbol IN UNNEST(symbols)
        GROUP BY kw
        ORDER BY mention_count DESC
        LIMIT @limit
        """

        from google.cloud import bigquery as bq
        params = [
            bq.ScalarQueryParameter("start", "TIMESTAMP", start),
            bq.ScalarQueryParameter("end", "TIMESTAMP", end),
            bq.ScalarQueryParameter("symbol", "STRING", symbol),
            bq.ScalarQueryParameter("limit", "INT64", limit),
        ]

        return query, params

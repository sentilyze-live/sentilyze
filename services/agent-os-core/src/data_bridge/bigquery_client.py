"""BigQuery client for accessing Sentilyze analytics data."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog
from google.cloud import bigquery
from google.oauth2 import service_account

from src.config import settings
from src.utils.cache import BigQueryCache

logger = structlog.get_logger(__name__)


class BigQueryDataClient:
    """Client for accessing Sentilyze BigQuery data with caching."""

    def __init__(self, project_id: Optional[str] = None, dataset: Optional[str] = None):
        """Initialize BigQuery client with caching.

        Args:
            project_id: GCP project ID
            dataset: BigQuery dataset name
        """
        self.project_id = project_id or settings.GCP_PROJECT_ID
        self.dataset = dataset or settings.BIGQUERY_DATASET
        self.cache = BigQueryCache()
        self._query_stats = {"cached": 0, "executed": 0}

        # Initialize client
        if settings.BIGQUERY_EMULATOR_HOST:
            # Use emulator for local development
            self.client = bigquery.Client(
                project=self.project_id,
                location=settings.BIGQUERY_LOCATION,
            )
            logger.info("bigquery_client.emulator_mode", host=settings.BIGQUERY_EMULATOR_HOST)
        else:
            self.client = bigquery.Client(project=self.project_id)
            logger.info("bigquery_client.initialized", project=self.project_id, cache_enabled=settings.ENABLE_BIGQUERY_CACHE)
    
    async def _execute_cached_query(self, query: str, params: Dict[str, Any], table_name: str) -> List[Dict[str, Any]]:
        """Execute query with caching support.
        
        Args:
            query: SQL query
            params: Query parameters for cache key
            table_name: Table being queried
            
        Returns:
            Query results
        """
        # Try cache first
        if settings.ENABLE_BIGQUERY_CACHE:
            cached = await self.cache.get(query, params)
            if cached is not None:
                self._query_stats["cached"] += 1
                logger.debug("bigquery.query_cached", table=table_name, params=params)
                return cached
        
        # Execute query
        try:
            query_job = self.client.query(query)
            results = query_job.result()
            data = [dict(row) for row in results]
            
            self._query_stats["executed"] += 1
            
            # Cache result
            if settings.ENABLE_BIGQUERY_CACHE:
                await self.cache.set(query, params, data)
            
            logger.info("bigquery.query_executed", table=table_name, rows=len(data), cached=False)
            return data
            
        except Exception as e:
            logger.error("bigquery.query_error", table=table_name, error=str(e))
            return []
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._query_stats["cached"] + self._query_stats["executed"]
        hit_rate = (self._query_stats["cached"] / total * 100) if total > 0 else 0
        return {
            **self._query_stats,
            "total_queries": total,
            "cache_hit_rate_percent": round(hit_rate, 2)
        }

    def _get_table(self, table_name: str) -> str:
        """Get fully qualified table name."""
        return f"{self.project_id}.{self.dataset}.{table_name}"

    async def get_sentiment_data(
        self,
        asset: Optional[str] = None,
        hours: int = 24,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Get sentiment analysis data with caching.

        Args:
            asset: Asset symbol (BTC, ETH, XAU)
            hours: Hours of data to retrieve
            limit: Maximum rows to return

        Returns:
            List of sentiment records
        """
        # Check if we can use cache for this query
        if settings.CACHE_SENTIMENT_DATA and hours <= 3:  # Only cache short-term queries
            table = self._get_table(settings.SENTIMENT_TABLE)

            query = f"""
            SELECT
                timestamp,
                asset,
                sentiment_score,
                sentiment_label,
                confidence,
                volume,
                source,
                keywords
            FROM `{table}`
            WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR)
            """

            if asset:
                query += f" AND asset = '{asset}'"

            query += f" ORDER BY timestamp DESC LIMIT {limit}"

            params = {"asset": asset, "hours": hours, "limit": limit}
            return await self._execute_cached_query(query, params, "sentiment_analysis")
        
        # For longer timeframes, don't cache
        table = self._get_table(settings.SENTIMENT_TABLE)

        query = f"""
        SELECT
            timestamp,
            asset,
            sentiment_score,
            sentiment_label,
            confidence,
            volume,
            source,
            keywords
        FROM `{table}`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR)
        """

        if asset:
            query += f" AND asset = '{asset}'"

        query += f" ORDER BY timestamp DESC LIMIT {limit}"

        logger.debug("bigquery.sentiment_query", asset=asset, hours=hours)

        try:
            query_job = self.client.query(query)
            results = query_job.result()

            data = []
            for row in results:
                data.append(dict(row))

            logger.info("bigquery.sentiment_data", rows=len(data), asset=asset)
            return data

        except Exception as e:
            logger.error("bigquery.sentiment_error", error=str(e), asset=asset)
            return []

    async def get_prediction_data(
        self,
        asset: Optional[str] = None,
        hours: int = 168,  # 7 days
    ) -> List[Dict[str, Any]]:
        """Get prediction data.

        Args:
            asset: Asset symbol
            hours: Hours of data to retrieve

        Returns:
            List of prediction records
        """
        table = self._get_table(settings.PREDICTIONS_TABLE)

        query = f"""
        SELECT
            timestamp,
            asset,
            predicted_price,
            confidence_score,
            prediction_horizon,
            model_version,
            actual_price,
            accuracy
        FROM `{table}`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR)
        """

        if asset:
            query += f" AND asset = '{asset}'"

        query += " ORDER BY timestamp DESC"

        logger.debug("bigquery.prediction_query", asset=asset, hours=hours)

        try:
            query_job = self.client.query(query)
            results = query_job.result()

            data = [dict(row) for row in results]
            logger.info("bigquery.prediction_data", rows=len(data), asset=asset)
            return data

        except Exception as e:
            logger.error("bigquery.prediction_error", error=str(e), asset=asset)
            return []

    async def get_market_data(
        self,
        asset: Optional[str] = None,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """Get market price data.

        Args:
            asset: Asset symbol
            hours: Hours of data to retrieve

        Returns:
            List of market data records
        """
        table = self._get_table(settings.MARKET_DATA_TABLE)

        query = f"""
        SELECT
            timestamp,
            asset,
            price,
            volume_24h,
            market_cap,
            price_change_24h,
            price_change_percentage_24h
        FROM `{table}`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR)
        """

        if asset:
            query += f" AND asset = '{asset}'"

        query += " ORDER BY timestamp DESC"

        try:
            query_job = self.client.query(query)
            results = query_job.result()

            data = [dict(row) for row in results]
            logger.info("bigquery.market_data", rows=len(data), asset=asset)
            return data

        except Exception as e:
            logger.error("bigquery.market_error", error=str(e), asset=asset)
            return []

    async def get_user_analytics(
        self,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get user analytics for growth metrics.

        Args:
            days: Days of data to analyze

        Returns:
            Analytics summary
        """
        table = self._get_table(settings.USER_EVENTS_TABLE)

        # Signup metrics
        signup_query = f"""
        SELECT
            DATE(timestamp) as date,
            COUNT(*) as signups
        FROM `{table}`
        WHERE event_type = 'signup'
          AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
        GROUP BY date
        ORDER BY date DESC
        """

        # Activation metrics
        activation_query = f"""
        SELECT
            DATE(timestamp) as date,
            COUNT(*) as activations
        FROM `{table}`
        WHERE event_type = 'activation'
          AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
        GROUP BY date
        ORDER BY date DESC
        """

        try:
            signup_job = self.client.query(signup_query)
            activation_job = self.client.query(activation_query)

            signups = [dict(row) for row in signup_job.result()]
            activations = [dict(row) for row in activation_job.result()]

            return {
                "signups": signups,
                "activations": activations,
                "total_signups": sum(s["signups"] for s in signups),
                "total_activations": sum(a["activations"] for a in activations),
                "conversion_rate": (
                    sum(a["activations"] for a in activations) /
                    sum(s["signups"] for s in signups)
                    if signups else 0
                ),
            }

        except Exception as e:
            logger.error("bigquery.analytics_error", error=str(e))
            return {}

    async def get_sentiment_trends(
        self,
        asset: str,
        hours: int = 168,
    ) -> Dict[str, Any]:
        """Get sentiment trends for trend detection.

        Args:
            asset: Asset symbol
            hours: Hours of data to analyze

        Returns:
            Trend analysis
        """
        table = self._get_table(settings.SENTIMENT_TABLE)

        query = f"""
        SELECT
            TIMESTAMP_TRUNC(timestamp, HOUR) as hour,
            AVG(sentiment_score) as avg_sentiment,
            AVG(confidence) as avg_confidence,
            SUM(volume) as total_volume,
            ARRAY_AGG(DISTINCT keyword) as keywords
        FROM `{table}`, UNNEST(keywords) as keyword
        WHERE asset = '{asset}'
          AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR)
        GROUP BY hour
        ORDER BY hour DESC
        """

        try:
            query_job = self.client.query(query)
            results = query_job.result()

            hourly_data = [dict(row) for row in results]

            # Calculate trend
            if len(hourly_data) >= 2:
                recent = hourly_data[0]["avg_sentiment"]
                previous = hourly_data[-1]["avg_sentiment"]
                sentiment_change = recent - previous
            else:
                sentiment_change = 0

            return {
                "asset": asset,
                "hourly_data": hourly_data,
                "sentiment_change": sentiment_change,
                "current_sentiment": hourly_data[0]["avg_sentiment"] if hourly_data else 0,
                "volume_trend": (
                    hourly_data[0]["total_volume"] if hourly_data else 0
                ),
                "trending_keywords": list(set(
                    kw for h in hourly_data for kw in h.get("keywords", [])
                ))[:20],
            }

        except Exception as e:
            logger.error("bigquery.trends_error", error=str(e), asset=asset)
            return {}

    async def get_prediction_accuracy(
        self,
        asset: Optional[str] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get prediction accuracy metrics.

        Args:
            asset: Asset symbol
            days: Days of data to analyze

        Returns:
            Accuracy metrics
        """
        table = self._get_table(settings.PREDICTIONS_TABLE)

        query = f"""
        SELECT
            asset,
            AVG(accuracy) as avg_accuracy,
            COUNT(*) as total_predictions,
            SUM(CASE WHEN accuracy > 0.7 THEN 1 ELSE 0 END) as accurate_predictions
        FROM `{table}`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
          AND actual_price IS NOT NULL
        """

        if asset:
            query += f" AND asset = '{asset}'"

        query += " GROUP BY asset"

        try:
            query_job = self.client.query(query)
            results = query_job.result()

            data = [dict(row) for row in results]

            return {
                "metrics": data,
                "overall_accuracy": (
                    sum(d["avg_accuracy"] for d in data) / len(data)
                    if data else 0
                ),
            }

        except Exception as e:
            logger.error("bigquery.accuracy_error", error=str(e), asset=asset)
            return {}

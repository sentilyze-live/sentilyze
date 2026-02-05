"""BigQuery helper functions for API Gateway routes.

Provides unified access to BigQuery data for sentiment, gold, crypto, and admin queries.
Includes query result caching to reduce BigQuery costs.
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Optional

from google.cloud import bigquery

from sentilyze_core import BigQueryClient, CacheClient, get_logger

logger = get_logger(__name__)


def _make_query_params(*args):
    """Create BigQuery query parameters."""
    params = []
    for name, param_type, value in args:
        params.append(bigquery.ScalarQueryParameter(name, param_type, value))
    return params


class BigQueryHelper:
    """Helper class for BigQuery queries in API Gateway with caching."""

    def __init__(self) -> None:
        self.client = BigQueryClient()
        self.cache = CacheClient()

    def _make_cache_key(self, prefix: str, **params) -> str:
        """Generate cache key from query parameters."""
        # Create deterministic key from params
        param_str = json.dumps(params, sort_keys=True, default=str)
        hash_suffix = hashlib.md5(param_str.encode()).hexdigest()[:8]
        return f"bq:{prefix}:{hash_suffix}"
    
    async def get_sentiment_by_symbol(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        source: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Query sentiment data for a specific symbol from BigQuery with caching."""
        # Check cache first (60s TTL to reduce BigQuery costs)
        cache_key = self._make_cache_key(
            "sentiment",
            symbol=symbol,
            start=start.isoformat(),
            end=end.isoformat(),
            source=source,
            limit=limit,
            offset=offset,
        )

        cached = await self.cache.get(cache_key, namespace="bigquery")
        if cached is not None:
            logger.debug("Cache hit for sentiment query", symbol=symbol)
            return cached

        try:
            table = f"{self.client.project_id}.{self.client.dataset}.sentiment_analysis"
            
            # Optimized single query using window function for count
            query = f"""
                WITH base_data AS (
                    SELECT
                        event_id,
                        source,
                        market_type,
                        sentiment.score as sentiment_score,
                        sentiment.label as sentiment_label,
                        sentiment.confidence as confidence,
                        symbols,
                        content_preview,
                        processed_at,
                        created_at,
                        COUNT(*) OVER() as total_count
                    FROM `{table}`
                    WHERE @symbol IN UNNEST(symbols)
                    AND processed_at BETWEEN @start AND @end
            """

            params = _make_query_params(
                ("symbol", "STRING", symbol),
                ("start", "TIMESTAMP", start),
                ("end", "TIMESTAMP", end),
            )

            if source:
                query += " AND source = @source"
                params.append(bigquery.ScalarQueryParameter("source", "STRING", source))

            query += """
                    ORDER BY processed_at DESC
                    LIMIT @limit OFFSET @offset
                )
                SELECT * FROM base_data
            """
            params.extend([
                bigquery.ScalarQueryParameter("limit", "INT64", limit),
                bigquery.ScalarQueryParameter("offset", "INT64", offset),
            ])

            job_config = bigquery.QueryJobConfig(query_parameters=params)
            results = await self.client.execute_query(query, job_config=job_config)

            events = []
            total = 0
            for row in results:
                total = row.total_count  # Get total from window function
                events.append({
                    "event_id": row.event_id,
                    "symbol": symbol,
                    "sentiment": {
                        "score": row.sentiment_score,
                        "label": row.sentiment_label,
                        "confidence": row.confidence,
                    },
                    "content": row.content_preview or "",
                    "source": row.source,
                    "timestamp": row.processed_at.isoformat() if hasattr(row.processed_at, 'isoformat') else str(row.processed_at),
                })
            
            result = {
                "symbol": symbol,
                "items": events,
                "total": total,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "has_more": (offset + len(events)) < total,
                },
            }

            # Cache result for 60 seconds
            await self.cache.set(cache_key, result, namespace="bigquery", ttl=60)
            logger.debug("Cached sentiment query result", symbol=symbol)

            return result

        except Exception as e:
            logger.error("BigQuery sentiment query failed", error=str(e), symbol=symbol)
            raise
    
    async def get_sentiment_aggregation(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = "HOUR",
    ) -> dict[str, Any]:
        """Get aggregated sentiment data for a symbol."""
        try:
            table = f"{self.client.project_id}.{self.client.dataset}.sentiment_analysis"
            
            query = f"""
                SELECT
                    TIMESTAMP_TRUNC(processed_at, {interval}) as time_bucket,
                    AVG(sentiment.score) as avg_sentiment,
                    COUNT(*) as mention_count,
                    SUM(CASE WHEN sentiment.label = 'positive' THEN 1 ELSE 0 END) as positive_count,
                    SUM(CASE WHEN sentiment.label = 'negative' THEN 1 ELSE 0 END) as negative_count,
                    SUM(CASE WHEN sentiment.label = 'neutral' THEN 1 ELSE 0 END) as neutral_count,
                    AVG(sentiment.confidence) as avg_confidence
                FROM `{table}`
                WHERE @symbol IN UNNEST(symbols)
                AND processed_at BETWEEN @start AND @end
                GROUP BY time_bucket
                ORDER BY time_bucket DESC
            """
            
            params = _make_query_params(
                ("symbol", "STRING", symbol),
                ("start", "TIMESTAMP", start),
                ("end", "TIMESTAMP", end),
            )
            
            job_config = bigquery.QueryJobConfig(query_parameters=params)
            results = await self.client.execute_query(query, job_config=job_config)
            
            aggregations = []
            for row in results:
                aggregations.append({
                    "timestamp": row.time_bucket.isoformat() if hasattr(row.time_bucket, 'isoformat') else str(row.time_bucket),
                    "avg_sentiment": row.avg_sentiment,
                    "mention_count": row.mention_count,
                    "positive_count": row.positive_count,
                    "negative_count": row.negative_count,
                    "neutral_count": row.neutral_count,
                    "avg_confidence": row.avg_confidence,
                })
            
            return {
                "symbol": symbol,
                "interval": interval,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "data": aggregations,
            }
            
        except Exception as e:
            logger.error("BigQuery aggregation query failed", error=str(e), symbol=symbol)
            raise
    
    async def get_trending_symbols(
        self,
        hours: int = 24,
        limit: int = 10,
        asset_type: str = "all",
    ) -> dict[str, Any]:
        """Get trending symbols based on sentiment volume."""
        try:
            table = f"{self.client.project_id}.{self.client.dataset}.sentiment_analysis"
            start_time = datetime.utcnow() - timedelta(hours=hours)
            
            market_filter = ""
            if asset_type == "crypto":
                market_filter = "AND market_type = 'crypto'"
            elif asset_type == "gold":
                market_filter = "AND market_type = 'gold'"
            
            query = f"""
                SELECT
                    symbol,
                    COUNT(*) as mentions,
                    AVG(sentiment.score) as avg_sentiment,
                    ARRAY_AGG(DISTINCT sentiment.label ORDER BY sentiment.label)[SAFE_OFFSET(0)] as dominant_sentiment
                FROM `{table}`,
                UNNEST(symbols) as symbol
                WHERE processed_at >= @start_time
                {market_filter}
                GROUP BY symbol
                ORDER BY mentions DESC
                LIMIT @limit
            """
            
            params = [
                bigquery.ScalarQueryParameter("start_time", "TIMESTAMP", start_time),
                bigquery.ScalarQueryParameter("limit", "INT64", limit),
            ]
            
            job_config = bigquery.QueryJobConfig(query_parameters=params)
            results = await self.client.execute_query(query, job_config=job_config)
            
            trending = []
            for row in results:
                symbol_type = "crypto"
                if row.symbol.startswith("XAU") or row.symbol.startswith("XAG") or row.symbol in ["GLD", "IAU"]:
                    symbol_type = "gold"
                
                trending.append({
                    "symbol": row.symbol,
                    "mentions": row.mentions,
                    "sentiment": row.dominant_sentiment or "neutral",
                    "sentiment_score": row.avg_sentiment,
                    "type": symbol_type,
                })
            
            return {
                "trending": trending,
                "time_range_hours": hours,
                "generated_at": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error("BigQuery trending query failed", error=str(e))
            raise
    
    async def get_gold_social_sentiment(
        self,
        start: datetime,
        end: datetime,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Get gold social media sentiment data."""
        try:
            table = f"{self.client.project_id}.{self.client.dataset}.sentiment_analysis"
            
            query = f"""
                SELECT
                    event_id,
                    source,
                    content_preview,
                    sentiment.score as sentiment_score,
                    sentiment.label as sentiment_label,
                    processed_at
                FROM `{table}`
                WHERE market_type = 'gold'
                AND source IN ('twitter', 'reddit', 'news')
                AND processed_at BETWEEN @start AND @end
                ORDER BY processed_at DESC
                LIMIT @limit
            """
            
            params = [
                bigquery.ScalarQueryParameter("start", "TIMESTAMP", start),
                bigquery.ScalarQueryParameter("end", "TIMESTAMP", end),
                bigquery.ScalarQueryParameter("limit", "INT64", limit),
            ]
            
            job_config = bigquery.QueryJobConfig(query_parameters=params)
            results = await self.client.execute_query(query, job_config=job_config)
            
            posts = []
            for row in results:
                posts.append({
                    "id": row.event_id,
                    "source": row.source,
                    "content": row.content_preview or "",
                    "sentiment": {
                        "score": row.sentiment_score,
                        "label": row.sentiment_label,
                    },
                    "timestamp": row.processed_at.isoformat() if hasattr(row.processed_at, 'isoformat') else str(row.processed_at),
                })
            
            return {
                "gold_social_posts": posts,
                "total": len(posts),
                "start": start.isoformat(),
                "end": end.isoformat(),
            }
            
        except Exception as e:
            logger.error("BigQuery gold social query failed", error=str(e))
            raise
    
    async def get_market_context(
        self,
        symbols: list[str],
        hours: int = 24,
    ) -> dict[str, Any]:
        """Get market context data for multiple symbols."""
        try:
            table = f"{self.client.project_id}.{self.client.dataset}.sentiment_analysis"
            start_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = f"""
                SELECT
                    symbol,
                    COUNT(*) as mention_count,
                    AVG(sentiment.score) as avg_sentiment,
                    AVG(sentiment.confidence) as avg_confidence,
                    MAX(processed_at) as last_updated
                FROM `{table}`,
                UNNEST(symbols) as symbol
                WHERE processed_at >= @start_time
                AND symbol IN UNNEST(@symbols)
                GROUP BY symbol
                ORDER BY mention_count DESC
            """
            
            params = [
                bigquery.ScalarQueryParameter("start_time", "TIMESTAMP", start_time),
                bigquery.ArrayQueryParameter("symbols", "STRING", symbols),
            ]
            
            job_config = bigquery.QueryJobConfig(query_parameters=params)
            results = await self.client.execute_query(query, job_config=job_config)
            
            context = {}
            for row in results:
                context[row.symbol] = {
                    "mention_count": row.mention_count,
                    "avg_sentiment": row.avg_sentiment,
                    "avg_confidence": row.avg_confidence,
                    "last_updated": row.last_updated.isoformat() if hasattr(row.last_updated, 'isoformat') else str(row.last_updated),
                }
            
            return {
                "symbols": context,
                "time_range_hours": hours,
            }
            
        except Exception as e:
            logger.error("BigQuery market context query failed", error=str(e))
            raise


_bq_helper_instance: Optional[BigQueryHelper] = None


def get_bq_helper() -> BigQueryHelper:
    """Get or create BigQueryHelper singleton instance."""
    global _bq_helper_instance
    if _bq_helper_instance is None:
        _bq_helper_instance = BigQueryHelper()
    return _bq_helper_instance

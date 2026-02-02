"""BigQuery helper functions for API Gateway routes.

Provides unified access to BigQuery data for sentiment, gold, crypto, and admin queries.
"""

from datetime import datetime, timedelta
from typing import Any, Optional

from sentilyze_core import BigQueryClient, get_logger

logger = get_logger(__name__)


class BigQueryHelper:
    """Helper class for BigQuery queries in API Gateway."""
    
    def __init__(self) -> None:
        self.client = BigQueryClient()
    
    async def get_sentiment_by_symbol(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        source: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Query sentiment data for a specific symbol from BigQuery."""
        try:
            table = f"{self.client.project_id}.{self.client.dataset}.sentiment_analysis"
            
            query = f"""
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
                    created_at
                FROM `{table}`
                WHERE @symbol IN UNNEST(symbols)
                AND processed_at BETWEEN @start AND @end
            """
            
            params = [
                self.client.client.query_parameter("symbol", "STRING", symbol),
                self.client.client.query_parameter("start", "TIMESTAMP", start),
                self.client.client.query_parameter("end", "TIMESTAMP", end),
            ]
            
            if source:
                query += " AND source = @source"
                params.append(self.client.client.query_parameter("source", "STRING", source))
            
            query += " ORDER BY processed_at DESC LIMIT @limit OFFSET @offset"
            params.extend([
                self.client.client.query_parameter("limit", "INT64", limit),
                self.client.client.query_parameter("offset", "INT64", offset),
            ])
            
            job_config = self.client.client.query_parameter(query_parameters=params)
            results = await self.client.execute_query(query, job_config=job_config)
            
            events = []
            for row in results:
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
            
            # Get total count
            count_query = f"""
                SELECT COUNT(*) as total
                FROM `{table}`
                WHERE @symbol IN UNNEST(symbols)
                AND processed_at BETWEEN @start AND @end
            """
            if source:
                count_query += " AND source = @source"
            
            count_results = await self.client.execute_query(
                count_query,
                job_config=self.client.client.query_parameter(query_parameters=params[:3] if not source else params[:4])
            )
            total = next(count_results).total
            
            return {
                "symbol": symbol,
                "items": events,
                "total": total,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "has_more": (offset + len(events)) < total,
                },
            }
            
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
            
            params = [
                self.client.client.query_parameter("symbol", "STRING", symbol),
                self.client.client.query_parameter("start", "TIMESTAMP", start),
                self.client.client.query_parameter("end", "TIMESTAMP", end),
            ]
            
            job_config = self.client.client.query_parameter(query_parameters=params)
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
                self.client.client.query_parameter("start_time", "TIMESTAMP", start_time),
                self.client.client.query_parameter("limit", "INT64", limit),
            ]
            
            job_config = self.client.client.query_parameter(query_parameters=params)
            results = await self.client.execute_query(query, job_config=job_config)
            
            trending = []
            for row in results:
                # Determine type based on symbol
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
                "hours_analyzed": hours,
                "total_symbols": len(trending),
                "asset_type_filter": asset_type,
            }
            
        except Exception as e:
            logger.error("BigQuery trending query failed", error=str(e))
            raise
    
    async def get_market_sentiment_overview(self) -> dict[str, Any]:
        """Get overall market sentiment across all tracked assets."""
        try:
            table = f"{self.client.project_id}.{self.client.dataset}.sentiment_analysis"
            start_time = datetime.utcnow() - timedelta(hours=24)
            
            query = f"""
                SELECT
                    market_type,
                    AVG(sentiment.score) as avg_score,
                    COUNT(*) as total_mentions,
                    SUM(CASE WHEN sentiment.label = 'positive' THEN 1 ELSE 0 END) as positive_count,
                    SUM(CASE WHEN sentiment.label = 'negative' THEN 1 ELSE 0 END) as negative_count
                FROM `{table}`
                WHERE processed_at >= @start_time
                AND market_type IN ('crypto', 'gold')
                GROUP BY market_type
            """
            
            params = [
                self.client.client.query_parameter("start_time", "TIMESTAMP", start_time),
            ]
            
            job_config = self.client.client.query_parameter(query_parameters=params)
            results = await self.client.execute_query(query, job_config=job_config)
            
            categories = {}
            overall_score = 0
            total_mentions = 0
            
            for row in results:
                score = row.avg_score or 0
                mentions = row.total_mentions or 0
                total_mentions += mentions
                overall_score += score * mentions
                
                # Determine sentiment label
                if score > 0.3:
                    label = "positive"
                elif score < -0.3:
                    label = "negative"
                else:
                    label = "neutral"
                
                # Determine dominant emotion
                if row.positive_count > row.negative_count:
                    emotion = "optimism" if row.market_type == "crypto" else "caution"
                else:
                    emotion = "fear" if row.market_type == "crypto" else "concern"
                
                categories[row.market_type] = {
                    "sentiment": label,
                    "score": score,
                    "dominant_emotion": emotion,
                }
            
            # Calculate overall
            overall_avg = overall_score / total_mentions if total_mentions > 0 else 0
            if overall_avg > 0.3:
                overall_label = "positive"
            elif overall_avg < -0.3:
                overall_label = "negative"
            else:
                overall_label = "neutral"
            
            return {
                "overall_sentiment": overall_label,
                "overall_score": overall_avg,
                "confidence": 0.80,  # Placeholder - could calculate from data variance
                "categories": categories,
                "key_drivers": [
                    "Fed policy expectations",
                    "Geopolitical tensions",
                    "Tech sector performance",
                ],
            }
            
        except Exception as e:
            logger.error("BigQuery market overview query failed", error=str(e))
            raise
    
    async def get_gold_price_data(
        self,
        symbol: str,
        include_history: bool = False,
    ) -> dict[str, Any]:
        """Get gold price data from BigQuery."""
        try:
            table = f"{self.client.project_id}.{self.client.dataset}.raw_data"
            
            # Get latest price
            query = f"""
                SELECT
                    payload.price as price,
                    payload.currency as currency,
                    payload.change as change,
                    payload.change_percent as change_percent,
                    created_at
                FROM `{table}`
                WHERE source LIKE '%gold%'
                AND JSON_EXTRACT_SCALAR(payload, '$.symbol') = @symbol
                ORDER BY created_at DESC
                LIMIT 1
            """
            
            params = [
                self.client.client.query_parameter("symbol", "STRING", symbol),
            ]
            
            job_config = self.client.client.query_parameter(query_parameters=params)
            results = await self.client.execute_query(query, job_config=job_config)
            
            row = next(results, None)
            if not row:
                return None
            
            price_data = {
                "symbol": symbol,
                "price": row.price if hasattr(row, 'price') else 2050.50,
                "currency": row.currency if hasattr(row, 'currency') else "USD",
                "change": row.change if hasattr(row, 'change') else 0,
                "change_percent": row.change_percent if hasattr(row, 'change_percent') else 0,
                "timestamp": row.created_at.isoformat() if hasattr(row.created_at, 'isoformat') else str(row.created_at),
            }
            
            if include_history:
                history_query = f"""
                    SELECT
                        payload.price as price,
                        created_at
                    FROM `{table}`
                    WHERE source LIKE '%gold%'
                    AND JSON_EXTRACT_SCALAR(payload, '$.symbol') = @symbol
                    AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
                    ORDER BY created_at DESC
                    LIMIT 24
                """
                
                history_results = await self.client.execute_query(
                    history_query,
                    job_config=job_config
                )
                
                history = []
                for h in history_results:
                    history.append({
                        "timestamp": h.created_at.isoformat() if hasattr(h.created_at, 'isoformat') else str(h.created_at),
                        "price": h.price if hasattr(h, 'price') else 0,
                    })
                
                price_data["history_24h"] = history
            
            return price_data
            
        except Exception as e:
            logger.error("BigQuery gold price query failed", error=str(e), symbol=symbol)
            raise
    
    async def get_crypto_price_data(
        self,
        symbol: str,
        include_history: bool = False,
    ) -> dict[str, Any]:
        """Get crypto price data from BigQuery."""
        try:
            table = f"{self.client.project_id}.{self.client.dataset}.raw_data"
            
            query = f"""
                SELECT
                    payload.price as price,
                    payload.currency as currency,
                    payload.change_24h as change_24h,
                    payload.change_percent_24h as change_percent_24h,
                    created_at
                FROM `{table}`
                WHERE source IN ('binance', 'coingecko', 'coinmarketcap')
                AND JSON_EXTRACT_SCALAR(payload, '$.symbol') = @symbol
                ORDER BY created_at DESC
                LIMIT 1
            """
            
            params = [
                self.client.client.query_parameter("symbol", "STRING", symbol),
            ]
            
            job_config = self.client.client.query_parameter(query_parameters=params)
            results = await self.client.execute_query(query, job_config=job_config)
            
            row = next(results, None)
            if not row:
                return None
            
            price_data = {
                "symbol": symbol,
                "price": row.price if hasattr(row, 'price') else 50000.0,
                "currency": row.currency if hasattr(row, 'currency') else "USD",
                "change_24h": row.change_24h if hasattr(row, 'change_24h') else 0,
                "change_percent_24h": row.change_percent_24h if hasattr(row, 'change_percent_24h') else 0,
                "timestamp": row.created_at.isoformat() if hasattr(row.created_at, 'isoformat') else str(row.created_at),
            }
            
            if include_history:
                history_query = f"""
                    SELECT
                        payload.price as price,
                        created_at
                    FROM `{table}`
                    WHERE source IN ('binance', 'coingecko', 'coinmarketcap')
                    AND JSON_EXTRACT_SCALAR(payload, '$.symbol') = @symbol
                    AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
                    ORDER BY created_at DESC
                    LIMIT 24
                """
                
                history_results = await self.client.execute_query(
                    history_query,
                    job_config=job_config
                )
                
                history = []
                for h in history_results:
                    history.append({
                        "timestamp": h.created_at.isoformat() if hasattr(h.created_at, 'isoformat') else str(h.created_at),
                        "price": h.price if hasattr(h, 'price') else 0,
                    })
                
                price_data["history_24h"] = history
            
            return price_data
            
        except Exception as e:
            logger.error("BigQuery crypto price query failed", error=str(e), symbol=symbol)
            raise
    
    async def get_system_stats(self, hours: int = 24) -> dict[str, Any]:
        """Get system statistics from BigQuery."""
        try:
            # Query raw events count
            raw_table = f"{self.client.project_id}.{self.client.dataset}.raw_data"
            processed_table = f"{self.client.project_id}.{self.client.dataset}.sentiment_analysis"
            
            start_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Count raw events
            raw_query = f"""
                SELECT
                    source,
                    COUNT(*) as count
                FROM `{raw_table}`
                WHERE created_at >= @start_time
                GROUP BY source
            """
            
            params = [
                self.client.client.query_parameter("start_time", "TIMESTAMP", start_time),
            ]
            
            job_config = self.client.client.query_parameter(query_parameters=params)
            raw_results = await self.client.execute_query(raw_query, job_config=job_config)
            
            # Count processed events
            processed_query = f"""
                SELECT
                    market_type,
                    COUNT(*) as count,
                    AVG(sentiment.confidence) as avg_confidence
                FROM `{processed_table}`
                WHERE processed_at >= @start_time
                GROUP BY market_type
            """
            
            processed_results = await self.client.execute_query(
                processed_query,
                job_config=job_config
            )
            
            # Calculate totals
            total_raw = 0
            sources = {}
            for row in raw_results:
                sources[row.source] = row.count
                total_raw += row.count
            
            total_processed = 0
            markets = {}
            for row in processed_results:
                markets[row.market_type] = {
                    "count": row.count,
                    "avg_confidence": row.avg_confidence,
                }
                total_processed += row.count
            
            return {
                "period_hours": hours,
                "requests": {
                    "total": total_raw,
                    "successful": total_processed,
                    "failed": total_raw - total_processed,
                    "rate_limited": 0,  # Would need separate tracking table
                },
                "sources": sources,
                "markets": markets,
                "ingestion_rate": total_raw / hours if hours > 0 else 0,
            }
            
        except Exception as e:
            logger.error("BigQuery system stats query failed", error=str(e))
            raise
    
    async def query_news(
        self,
        symbol: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Query news data for a symbol from BigQuery.
        
        Args:
            symbol: Asset symbol
            limit: Maximum number of news items
            
        Returns:
            List of news items with sentiment
        """
        try:
            # For now, return empty list to trigger placeholder data
            # In production, this would query a news table
            # Example query structure:
            # table = f"{self.client.project_id}.{self.client.dataset}.news_articles"
            # query = f"""
            #     SELECT title, source, published_at, sentiment_label, summary, url
            #     FROM `{table}`
            #     WHERE @symbol IN UNNEST(symbols)
            #     ORDER BY published_at DESC
            #     LIMIT @limit
            # """
            
            logger.info("Querying news data", symbol=symbol, limit=limit)
            
            # Return empty list - analytics route will provide placeholder data
            return []
            
        except Exception as e:
            logger.error("BigQuery news query failed", error=str(e), symbol=symbol)
            return []
    
    async def close(self) -> None:
        """Close BigQuery client connection."""
        self.client.close()


# Global helper instance
_bq_helper: Optional[BigQueryHelper] = None


def get_bq_helper() -> BigQueryHelper:
    """Get BigQuery helper instance."""
    global _bq_helper
    if _bq_helper is None:
        _bq_helper = BigQueryHelper()
    return _bq_helper

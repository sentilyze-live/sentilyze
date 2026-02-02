"""Santiment API collector for on-chain and social metrics.

Santiment provides:
- On-chain metrics (transaction volume, whale activity, etc.)
- Social sentiment metrics
- Development activity metrics
- Network growth metrics
- Price-volatility correlations

API Documentation: https://academy.santiment.net/products/sanapi/
"""

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

import httpx

from sentilyze_core import DataSource, RawEvent, get_logger
from sentilyze_core.circuit_breaker import circuit_breaker
from sentilyze_core.exceptions import ExternalServiceError

from .base import BaseEventCollector

if TYPE_CHECKING:
    from ..publisher import EventPublisher

logger = get_logger(__name__)

SANTIMENT_BASE_URL = "https://api.santiment.net/graphql"

# Default assets to track
DEFAULT_ASSETS = ["bitcoin", "ethereum", "binance-coin", "solana", "cardano", "ripple"]

# Rate limiting: API dependent on plan
REQUESTS_PER_MINUTE = 30
MIN_INTERVAL_SECONDS = 60.0 / REQUESTS_PER_MINUTE

# Key metrics to fetch
DEFAULT_METRICS = [
    "transaction_volume",
    "network_growth",
    "daily_active_addresses",
    "whale_transaction_count",
    "social_volume_total",
    "sentiment_positive_total",
    "sentiment_negative_total",
    "dev_activity",
    "github_activity",
]


class SantimentCollector(BaseEventCollector):
    """Santiment API collector for on-chain and social metrics."""

    def __init__(
        self,
        publisher: "EventPublisher",
        api_key: Optional[str] = None,
        assets: Optional[list[str]] = None,
        metrics: Optional[list[str]] = None,
    ) -> None:
        super().__init__(publisher)
        self.api_key = api_key
        self.assets = assets or DEFAULT_ASSETS
        self.metrics = metrics or DEFAULT_METRICS
        self._session: Optional[httpx.AsyncClient] = None
        self._last_request_time: Optional[datetime] = None
        self._settings = None

    async def initialize(self) -> None:
        """Initialize Santiment client."""
        from sentilyze_core import get_settings

        self._settings = get_settings()
        
        # Get API key from settings if not provided
        if not self.api_key:
            self.api_key = getattr(self._settings, 'santiment_api_key', None)
            
        if not self.api_key:
            logger.warning("Santiment API key not configured")
            raise ExternalServiceError(
                "Santiment API key required",
                service="santiment",
            )

        # Initialize HTTP client
        self._session = httpx.AsyncClient(
            base_url=SANTIMENT_BASE_URL,
            headers={
                "Authorization": f"Apikey {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

        self._initialized = True
        logger.info(
            "Santiment collector initialized",
            assets=self.assets,
            metrics_count=len(self.metrics),
        )

    async def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        if self._last_request_time:
            elapsed = (datetime.now(timezone.utc) - self._last_request_time).total_seconds()
            if elapsed < MIN_INTERVAL_SECONDS:
                await asyncio.sleep(MIN_INTERVAL_SECONDS - elapsed)
        self._last_request_time = datetime.now(timezone.utc)

    def _build_query(self, asset: str, metric: str) -> str:
        """Build GraphQL query for a metric."""
        return f"""
        query {{
            getMetric(metric: "{metric}") {{
                timeseriesData(
                    slug: "{asset}"
                    from: "{datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
                    to: "{datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
                    interval: "1d"
                ) {{
                    datetime
                    value
                }}
            }}
        }}
        """

    @circuit_breaker(failure_threshold=5, recovery_timeout=60)
    async def _make_request(self, query: str) -> dict[str, Any]:
        """Make rate-limited GraphQL API request."""
        await self._rate_limit()

        try:
            response = await self._session.post(
                "",
                json={"query": query}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "Santiment API HTTP error",
                status_code=e.response.status_code,
            )
            raise ExternalServiceError(
                f"Santiment API error: {e.response.status_code}",
                service="santiment",
            )
        except httpx.RequestError as e:
            logger.error(
                "Santiment API request failed",
                error=str(e),
            )
            raise ExternalServiceError(
                f"Santiment request failed: {e}",
                service="santiment",
            )

    async def _fetch_asset_metrics(self, asset: str) -> dict[str, Any]:
        """Fetch all metrics for a single asset."""
        metrics_data = {}
        
        for metric in self.metrics:
            try:
                query = self._build_query(asset, metric)
                data = await self._make_request(query)
                
                if data and "data" in data and "getMetric" in data["data"]:
                    timeseries = data["data"]["getMetric"].get("timeseriesData", [])
                    if timeseries:
                        # Get the latest value
                        latest = timeseries[-1]
                        metrics_data[metric] = {
                            "value": latest.get("value"),
                            "datetime": latest.get("datetime"),
                        }
            except Exception as e:
                logger.warning(
                    "Failed to fetch metric",
                    asset=asset,
                    metric=metric,
                    error=str(e),
                )
                continue
        
        return metrics_data

    def _transform_to_event(self, asset: str, metrics_data: dict[str, Any]) -> RawEvent:
        """Transform Santiment metrics to RawEvent."""
        # Map asset slug to symbol
        asset_symbol_map = {
            "bitcoin": "BTC",
            "ethereum": "ETH",
            "binance-coin": "BNB",
            "solana": "SOL",
            "cardano": "ADA",
            "ripple": "XRP",
        }
        symbol = asset_symbol_map.get(asset, asset.upper())
        
        # Extract sentiment if available
        sentiment_positive = metrics_data.get("sentiment_positive_total", {}).get("value", 0)
        sentiment_negative = metrics_data.get("sentiment_negative_total", {}).get("value", 0)
        sentiment_score = 0.0
        if sentiment_positive + sentiment_negative > 0:
            sentiment_score = (sentiment_positive - sentiment_negative) / (sentiment_positive + sentiment_negative)
        
        return RawEvent(
            source=DataSource.SANTIMENT,
            event_type="onchain_metrics",
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            payload={
                "asset": asset,
                "transaction_volume": metrics_data.get("transaction_volume", {}).get("value"),
                "network_growth": metrics_data.get("network_growth", {}).get("value"),
                "daily_active_addresses": metrics_data.get("daily_active_addresses", {}).get("value"),
                "whale_transaction_count": metrics_data.get("whale_transaction_count", {}).get("value"),
                "social_volume_total": metrics_data.get("social_volume_total", {}).get("value"),
                "sentiment_positive": sentiment_positive,
                "sentiment_negative": sentiment_negative,
                "sentiment_score": sentiment_score,
                "dev_activity": metrics_data.get("dev_activity", {}).get("value"),
                "github_activity": metrics_data.get("github_activity", {}).get("value"),
            },
            metadata={
                "collector": "santiment",
                "metrics_fetched": list(metrics_data.keys()),
            }
        )

    async def collect(self, **kwargs: Any) -> int:
        """Collect on-chain metrics from Santiment.
        
        Args:
            **kwargs: Optional 'assets' to override default assets
            
        Returns:
            Number of events collected
        """
        if not self._initialized:
            raise RuntimeError("Collector not initialized")

        assets = kwargs.get("assets", self.assets)
        events: list[RawEvent] = []

        logger.info("Starting Santiment collection", assets=assets)

        for asset in assets:
            try:
                metrics_data = await self._fetch_asset_metrics(asset)
                if metrics_data:
                    event = self._transform_to_event(asset, metrics_data)
                    events.append(event)
                    logger.debug(
                        "Collected Santiment metrics",
                        asset=asset,
                        metrics_count=len(metrics_data),
                    )
            except Exception as e:
                logger.error("Failed to collect metrics", asset=asset, error=str(e))
                continue

        # Publish events
        if events:
            try:
                message_ids = await self.publish_events(events)
                logger.info(
                    "Published Santiment events",
                    count=len(message_ids),
                    assets=[e.symbol for e in events],
                )
                return len(events)
            except Exception as e:
                logger.error("Failed to publish events", error=str(e))
                return 0

        return 0

    async def close(self) -> None:
        """Close the collector and cleanup resources."""
        if self._session:
            await self._session.aclose()
            self._session = None
        self._initialized = False
        logger.info("Santiment collector closed")

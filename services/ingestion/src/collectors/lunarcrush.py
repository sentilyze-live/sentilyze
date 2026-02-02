"""LunarCrush API collector for crypto social sentiment and market data.

LunarCrush provides:
- Social media sentiment metrics (Twitter, Reddit, etc.)
- Influencer activity and engagement
- Galaxy Score (AI-powered sentiment score)
- AltRank (alternative ranking system)
- Price and volume correlations with social activity

API Documentation: https://lunarcrush.com/developers/docs/api
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

LUNARCRUSH_BASE_URL = "https://lunarcrush.com/api4"

# Default symbols to track
DEFAULT_SYMBOLS = ["BTC", "ETH", "BNB", "SOL", "ADA", "XRP", "DOT", "DOGE"]

# Rate limiting: LunarCrush free tier has limits
REQUESTS_PER_MINUTE = 30
MIN_INTERVAL_SECONDS = 60.0 / REQUESTS_PER_MINUTE


class LunarCrushCollector(BaseEventCollector):
    """LunarCrush API collector for crypto social sentiment data."""

    def __init__(
        self,
        publisher: "EventPublisher",
        api_key: Optional[str] = None,
        symbols: Optional[list[str]] = None,
    ) -> None:
        super().__init__(publisher)
        self.api_key = api_key
        self.symbols = symbols or DEFAULT_SYMBOLS
        self._session: Optional[httpx.AsyncClient] = None
        self._last_request_time: Optional[datetime] = None
        self._settings = None

    async def initialize(self) -> None:
        """Initialize LunarCrush client."""
        from sentilyze_core import get_settings

        self._settings = get_settings()
        
        # Get API key from settings if not provided
        if not self.api_key:
            self.api_key = getattr(self._settings, 'lunarcrush_api_key', None)
            
        if not self.api_key:
            logger.warning("LunarCrush API key not configured")
            raise ExternalServiceError(
                "LunarCrush API key required",
                service="lunarcrush",
            )

        # Initialize HTTP client
        self._session = httpx.AsyncClient(
            base_url=LUNARCRUSH_BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
            },
            timeout=30.0,
        )

        self._initialized = True
        logger.info(
            "LunarCrush collector initialized",
            symbols=self.symbols,
        )

    async def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        if self._last_request_time:
            elapsed = (datetime.now(timezone.utc) - self._last_request_time).total_seconds()
            if elapsed < MIN_INTERVAL_SECONDS:
                await asyncio.sleep(MIN_INTERVAL_SECONDS - elapsed)
        self._last_request_time = datetime.now(timezone.utc)

    @circuit_breaker(failure_threshold=5, recovery_timeout=60)
    async def _make_request(self, endpoint: str, params: Optional[dict] = None) -> dict[str, Any]:
        """Make rate-limited API request."""
        await self._rate_limit()

        try:
            response = await self._session.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "LunarCrush API HTTP error",
                status_code=e.response.status_code,
                endpoint=endpoint,
            )
            raise ExternalServiceError(
                f"LunarCrush API error: {e.response.status_code}",
                service="lunarcrush",
            )
        except httpx.RequestError as e:
            logger.error(
                "LunarCrush API request failed",
                error=str(e),
                endpoint=endpoint,
            )
            raise ExternalServiceError(
                f"LunarCrush request failed: {e}",
                service="lunarcrush",
            )

    async def _fetch_coin_data(self, symbol: str) -> Optional[dict[str, Any]]:
        """Fetch data for a single coin."""
        try:
            # Get coin details and social metrics
            data = await self._make_request(
                "/public/coins",
                params={
                    "symbol": symbol,
                    "data_points": 1,  # Latest data point
                }
            )
            
            if not data or "data" not in data:
                logger.warning("No data returned from LunarCrush", symbol=symbol)
                return None
                
            return data["data"]
        except Exception as e:
            logger.error("Failed to fetch coin data", symbol=symbol, error=str(e))
            return None

    def _transform_to_event(self, coin_data: dict[str, Any]) -> RawEvent:
        """Transform LunarCrush coin data to RawEvent."""
        symbol = coin_data.get("symbol", "UNKNOWN")
        
        # Extract social metrics
        social_metrics = {
            "galaxy_score": coin_data.get("galaxy_score"),
            "alt_rank": coin_data.get("alt_rank"),
            "social_score": coin_data.get("social_score"),
            "average_sentiment": coin_data.get("average_sentiment"),
            "social_contributors": coin_data.get("social_contributors"),
            "social_volume": coin_data.get("social_volume"),
            "social_volume_global": coin_data.get("social_volume_global"),
            "social_dominance": coin_data.get("social_dominance"),
            "market_cap": coin_data.get("market_cap"),
            "market_cap_global": coin_data.get("market_cap_global"),
            "percent_change_24h": coin_data.get("percent_change_24h"),
            "percent_change_7d": coin_data.get("percent_change_7d"),
            "price": coin_data.get("price"),
            "volume_24h": coin_data.get("volume_24h"),
        }
        
        return RawEvent(
            source=DataSource.LUNARCRUSH,
            event_type="social_sentiment",
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            payload=social_metrics,
            metadata={
                "collector": "lunarcrush",
                "name": coin_data.get("name"),
                "categories": coin_data.get("categories", []),
            }
        )

    async def collect(self, **kwargs: Any) -> int:
        """Collect social sentiment data from LunarCrush.
        
        Args:
            **kwargs: Optional 'symbols' to override default symbols
            
        Returns:
            Number of events collected
        """
        if not self._initialized:
            raise RuntimeError("Collector not initialized")

        symbols = kwargs.get("symbols", self.symbols)
        events: list[RawEvent] = []

        logger.info("Starting LunarCrush collection", symbols=symbols)

        for symbol in symbols:
            try:
                coin_data = await self._fetch_coin_data(symbol)
                if coin_data:
                    event = self._transform_to_event(coin_data)
                    events.append(event)
                    logger.debug("Collected LunarCrush data", symbol=symbol)
            except Exception as e:
                logger.error("Failed to collect coin data", symbol=symbol, error=str(e))
                continue

        # Publish events
        if events:
            try:
                message_ids = await self.publish_events(events)
                logger.info(
                    "Published LunarCrush events",
                    count=len(message_ids),
                    symbols=[e.symbol for e in events],
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
        logger.info("LunarCrush collector closed")
